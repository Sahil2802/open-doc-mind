import pickle
import logging
import numpy as np
from rank_bm25 import BM25Okapi
from pinecone import Pinecone
from supabase import create_client
from backend.config.settings import settings

logger = logging.getLogger(__name__)

_pc = None
_index = None


def _get_index():
    global _pc, _index
    if _index is None:
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _index = _pc.Index(settings.PINECONE_INDEX_NAME)
    return _index

STORAGE_BUCKET = "system"
STORAGE_KEY = "bm25_index.pkl"

# Module-level cache for the BM25 index to avoid repeated Supabase downloads
_cached_bm25: BM25Okapi | None = None
_cached_pinecone_ids: list[str] = []


def rebuild_bm25_index(supabase_client) -> None:
    """
    Fetch all chunk texts from Pinecone metadata, build BM25 index,
    persist to Supabase Storage. Called after every successful ingestion.
    """
    global _cached_bm25, _cached_pinecone_ids

    try:
        pinecone_ids = []
        chunk_texts = []
        index = _get_index()

        # Pinecone list() paginates through all vector IDs
        for page in index.list():
            ids_batch = page
            if not ids_batch:
                continue

            # Fetch metadata for this batch
            fetch_response = index.fetch(ids=ids_batch)
            for vid, vector in fetch_response.vectors.items():
                pinecone_ids.append(vid)
                chunk_texts.append(vector.metadata.get("chunk_text", ""))

        if not chunk_texts:
            logger.warning("No chunks found in Pinecone. Skipping BM25 rebuild.")
            return

        # Tokenization fallback for simple BM25
        tokenized = [text.lower().split() for text in chunk_texts]
        bm25 = BM25Okapi(tokenized)

        # Ensure bucket exists
        buckets = supabase_client.storage.list_buckets()
        if not any(b.name == STORAGE_BUCKET for b in buckets):
            supabase_client.storage.create_bucket(STORAGE_BUCKET, options={"public": False})
            logger.info(f"Created missing storage bucket: {STORAGE_BUCKET}")

        # Serialize and upload to Supabase Storage
        payload = pickle.dumps({"bm25": bm25, "pinecone_ids": pinecone_ids})

        supabase_client.storage.from_(STORAGE_BUCKET).upload(
            path=STORAGE_KEY,
            file=payload,
            file_options={"upsert": "true"},
        )


        # Update module cache so we don't need to re-download
        _cached_bm25 = bm25
        _cached_pinecone_ids = pinecone_ids

        logger.info(f"Successfully rebuilt BM25 index with {len(chunk_texts)} chunks.")

    except Exception as e:
        logger.error(f"Failed to rebuild BM25 index: {e}", exc_info=True)


def load_bm25_index(supabase_client) -> tuple[BM25Okapi | None, list[str]]:
    """Download BM25 pickle from Supabase Storage on startup."""
    global _cached_bm25, _cached_pinecone_ids

    # Return from cache if available
    if _cached_bm25 is not None:
        return _cached_bm25, _cached_pinecone_ids

    try:
        data = supabase_client.storage.from_(STORAGE_BUCKET).download(STORAGE_KEY)
        loaded = pickle.loads(data)
        _cached_bm25 = loaded["bm25"]
        _cached_pinecone_ids = loaded["pinecone_ids"]
        logger.info(f"Loaded BM25 index with {len(_cached_pinecone_ids)} chunks from storage.")
        return _cached_bm25, _cached_pinecone_ids
    except Exception as e:
        logger.warning(f"Could not load BM25 index: {e}")
        return None, []


def bm25_search(query: str, top_k: int = 20) -> list[dict]:
    """
    Search using BM25 keyword matching.

    Returns top_k results sorted by BM25 score. Each result:
        - pinecone_id: str
        - score: float (raw BM25 score)
        - rank: int (0-based)

    Gracefully returns [] if no BM25 index is available,
    allowing the pipeline to fall back to vector-only search.
    """
    # Create a Supabase client to load the index
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    except Exception as e:
        logger.warning(f"Could not create Supabase client for BM25: {e}")
        return []

    bm25, pinecone_ids = load_bm25_index(supabase)

    if bm25 is None or not pinecone_ids:
        logger.info("BM25 index not available — falling back to vector-only search.")
        return []

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Get top_k indices by score, exclude zero-score results
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = [
        {
            "pinecone_id": pinecone_ids[idx],
            "score": float(scores[idx]),
            "rank": rank,
        }
        for rank, idx in enumerate(top_indices)
        if scores[idx] > 0
    ]

    logger.info(f"BM25 search returned {len(results)} results for query: {query[:80]!r}")
    return results


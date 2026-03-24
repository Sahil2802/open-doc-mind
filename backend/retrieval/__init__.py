import logging
from pinecone import Pinecone
from backend.config.settings import settings
from backend.retrieval.vector_retriever import vector_search
from backend.retrieval.bm25_retriever import bm25_search
from backend.retrieval.fusion import reciprocal_rank_fusion
from backend.retrieval.reranker import rerank

logger = logging.getLogger(__name__)

_pc = None
_index = None


def _get_index():
    global _pc, _index
    if _index is None:
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _index = _pc.Index(settings.PINECONE_INDEX_NAME)
    return _index


def retrieve_chunks(
    query: str,
    top_k: int = 20,
    final_top_n: int = 5,
    filter_document_id: str | None = None,
) -> list[dict]:
    """
    Full hybrid retrieval pipeline:
      1. Vector semantic search (Pinecone)
      2. BM25 keyword search (graceful fallback if unavailable)
      3. Reciprocal Rank Fusion (merges both result lists)
      4. Cross-encoder re-ranking (precise final scoring)

    All chunk data comes from Pinecone metadata — no Supabase call needed.

    Returns top_n chunks ready for the generation layer, each containing:
        - pinecone_id: str
        - score: float          # final normalized relevance score
        - chunk_text: str
        - file_name: str
        - page_number: int | None
        - chunk_index: int
        - reranker_score: float  # cross-encoder score (debug)
        - rrf_score: float       # fusion score (debug)
        - sources: list[str]     # which retrievers found this chunk
    """
    # Stage 1: Vector search
    vector_results = vector_search(
        query,
        top_k=top_k,
        filter_document_id=filter_document_id,
    )

    # Stage 2: BM25 keyword search (gracefully returns [] if index unavailable)
    bm25_results = bm25_search(query, top_k=top_k)

    # If both retrievers returned nothing, bail early
    if not vector_results and not bm25_results:
        logger.warning(f"No results from any retriever for query: {query[:80]!r}")
        return []

    # Stage 3: RRF Fusion
    if bm25_results:
        fused = reciprocal_rank_fusion([vector_results, bm25_results])
    else:
        # BM25 unavailable — treat vector results as the fused list
        fused = [
            {
                "pinecone_id": r["pinecone_id"],
                "rrf_score": r["score"],
                "sources": ["vector"],
            }
            for r in vector_results
        ]

    # Build metadata lookup from vector search results (already have include_metadata=True)
    vector_metadata = {r["pinecone_id"]: r["metadata"] for r in vector_results}

    # For chunks found only by BM25 (not in vector_results), fetch metadata from Pinecone
    candidate_pids = [f["pinecone_id"] for f in fused[:top_k]]
    missing_pids = [pid for pid in candidate_pids if pid not in vector_metadata]

    if missing_pids:
        try:
            index = _get_index()
            fetch_response = index.fetch(ids=missing_pids)
            for vid, vector in fetch_response.vectors.items():
                vector_metadata[vid] = vector.metadata
            logger.info(f"Fetched metadata for {len(missing_pids)} BM25-only chunks from Pinecone")
        except Exception as e:
            logger.error(f"Failed to fetch metadata for BM25-only chunks: {e}", exc_info=True)

    # Build chunk_texts lookup for the re-ranker
    chunk_texts = {
        pid: (vector_metadata.get(pid) or {}).get("chunk_text", "")
        for pid in candidate_pids
    }

    # Enrich fused results with full metadata
    enriched: list[dict] = []
    for candidate in fused[:top_k]:
        pid = candidate["pinecone_id"]
        meta = vector_metadata.get(pid, {})
        enriched.append({
            **candidate,
            "chunk_text": meta.get("chunk_text", ""),
            "file_name": meta.get("file_name", "unknown"),
            "page_number": meta.get("page_number"),
            "chunk_index": int(meta.get("chunk_index", 0)),
        })

    # Stage 4: Cross-encoder re-ranking
    reranked = rerank(query, enriched, chunk_texts, top_n=final_top_n)

    # Normalize output: set `score` to the most authoritative relevance score.
    # Priority: reranker_score > rrf_score (ensures a consistent contract
    # for all downstream consumers like context_builder and citation metadata).
    for chunk in reranked:
        chunk["score"] = (
            chunk.get("reranker_score")
            if chunk.get("reranker_score") is not None
            else chunk.get("rrf_score", 0.0)
        )

    logger.info(
        f"Hybrid retrieval complete — "
        f"vector={len(vector_results)}, bm25={len(bm25_results)}, "
        f"fused={len(fused)}, final={len(reranked)}"
    )
    return reranked

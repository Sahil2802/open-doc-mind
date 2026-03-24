import logging
from pinecone import Pinecone
from backend.config.settings import settings
from backend.ingestion.embedder import embed_query

logger = logging.getLogger(__name__)

_pc = None
_index = None


def _get_index():
    global _pc, _index
    if _index is None:
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _index = _pc.Index(settings.PINECONE_INDEX_NAME)
    return _index


def vector_search(
    query: str,
    top_k: int = 20,
    filter_document_id: str | None = None,
) -> list[dict]:
    """
    Embed the query and retrieve top-k results from Pinecone.

    Returns list of dicts, each containing:
        - pinecone_id: str
        - score: float (cosine similarity)
        - metadata: dict (includes chunk_text, file_name, page_number, etc.)

    Args:
        query: User's natural-language query string.
        top_k: Number of results to retrieve.
        filter_document_id: If set, restrict search to a single document.
    """
    query_embedding = embed_query(query)

    filter_dict = {}
    if filter_document_id:
        filter_dict["document_id"] = {"$eq": filter_document_id}

    try:
        index = _get_index()
        response = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None,
        )
    except Exception as e:
        logger.error(f"Pinecone query failed: {e}", exc_info=True)
        raise RuntimeError(f"Vector search failed: {e}") from e

    results = [
        {
            "pinecone_id": match.id,
            "score": match.score,
            "metadata": match.metadata,
        }
        for match in response.matches
    ]

    logger.info(f"Vector search returned {len(results)} results for query: {query[:80]!r}")
    return results

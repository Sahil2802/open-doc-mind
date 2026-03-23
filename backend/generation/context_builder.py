import logging

logger = logging.getLogger(__name__)


def build_context_block(chunks: list[dict]) -> tuple[str, list[dict]]:
    """
    Format retrieved chunks into a context string for the LLM prompt
    and build a citation map for the frontend.

    Args:
        chunks: List of enriched chunk dicts from retrieve_chunks(), each with
                pinecone_id, chunk_text, file_name, page_number, chunk_index, score.

    Returns:
        context_str: Formatted string injected into the user message.
        citation_map: List of citation metadata dicts for the frontend.
    """
    if not chunks:
        return "", []

    parts: list[str] = []
    citation_map: list[dict] = []

    for i, chunk in enumerate(chunks):
        page_info = (
            f", page {chunk['page_number']}"
            if chunk.get("page_number") is not None
            else ""
        )
        header = f"[Excerpt {i + 1} — Source: {chunk['file_name']}{page_info}]"
        parts.append(f"{header}\n{chunk['chunk_text']}")

        citation_map.append({
            "excerpt_number": i + 1,
            "file_name": chunk["file_name"],
            "page_number": chunk.get("page_number"),
            "chunk_index": chunk["chunk_index"],
            "chunk_text": chunk.get("chunk_text", ""),
            "pinecone_id": chunk["pinecone_id"],
            "score": chunk.get("score"),
            "reranker_score": chunk.get("reranker_score"),
        })

    context_str = "\n\n---\n\n".join(parts)

    logger.info(f"Built context block with {len(chunks)} excerpts")
    return context_str, citation_map

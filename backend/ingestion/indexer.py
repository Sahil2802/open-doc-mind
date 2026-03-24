import hashlib
from pinecone import Pinecone
from backend.config.settings import settings


_pc = None
_index = None


def _get_index():
    global _pc, _index
    if _index is None:
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _index = _pc.Index(settings.PINECONE_INDEX_NAME)
    return _index


def compute_file_hash(file_bytes: bytes) -> str:
    """SHA-256 hash used for idempotent ingestion and deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()


async def is_duplicate(file_hash: str, supabase_client) -> bool:
    """Check if a file with this hash already exists in the documents table."""
    result = supabase_client.table("documents") \
        .select("id") \
        .eq("file_hash", file_hash) \
        .execute()
    return len(result.data) > 0


async def store_file(
    file_bytes: bytes,
    file_name: str,
    document_id: str,
    supabase_client
) -> str:
    """Upload raw file to Supabase Storage."""
    storage_path = f"{document_id}/{file_name}"
    supabase_client.storage.from_("documents").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "application/octet-stream"}  # Generic for now
    )
    return storage_path


def upsert_to_pinecone(
    chunks: list[dict],
    embeddings: list[list[float]],
    document_id: str,
    file_name: str,
) -> None:
    """
    Upsert vectors in batches of 100.
    Metadata includes everything needed for citations: document_id, file_name,
    page_number, chunk_index, and the full chunk_text.
    """
    vectors = []
    for chunk, embedding in zip(chunks, embeddings):
        metadata = {
            "document_id": document_id,
            "file_name": file_name,
            "chunk_index": chunk["chunk_index"],
            "chunk_text": chunk["chunk_text"],
            "token_count": chunk["token_count"],
        }
        # Pinecone metadata doesn't allow nulls
        if chunk.get("page_number") is not None:
            metadata["page_number"] = chunk["page_number"]

        vectors.append({
            "id": chunk["pinecone_id"],
            "values": embedding,
            "metadata": metadata
        })

    # Batch upserts
    batch_size = 100
    index = _get_index()
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)

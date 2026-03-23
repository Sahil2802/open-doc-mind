from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer
import logging

logger = logging.getLogger(__name__)

# Lazy tokenizer init avoids crashing app startup when HF is unavailable in CI.
_tokenizer = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is not None:
        return _tokenizer

    try:
        _tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
    except Exception as exc:
        logger.warning(
            "Falling back to heuristic token counting; tokenizer load failed: %s",
            exc,
        )
        _tokenizer = False
    return _tokenizer


def count_tokens(text: str) -> int:
    tokenizer = _get_tokenizer()
    if tokenizer:
        return len(tokenizer.encode(text))

    # Rough fallback for environments without HF access (e.g., restricted CI).
    return max(1, len(text) // 4)


def token_length_function(text: str) -> int:
    return count_tokens(text)


_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,           # tokens
    chunk_overlap=100,        # tokens
    length_function=token_length_function,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_pages(pages: list[dict], file_hash: str) -> list[dict]:
    """
    Takes parsed pages, returns flat list of chunks with full metadata.

    Returns:
        list of {
            pinecone_id: str,
            chunk_index: int,
            chunk_text: str,
            page_number: int | None,
            token_count: int
        }
    """
    chunks = []
    global_index = 0

    for page in pages:
        page_chunks = _splitter.split_text(page["text"])
        for chunk_text in page_chunks:
            chunks.append({
                "pinecone_id": f"{file_hash}_{global_index}",
                "chunk_index": global_index,
                "chunk_text": chunk_text,
                "page_number": page["page_number"],
                "token_count": count_tokens(chunk_text),
            })
            global_index += 1

    return chunks

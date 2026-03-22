"""
Document parser for the RAG ingestion pipeline.

Supports plain text (.txt) and PDF files via PyMuPDF.
Returns a list of page dicts with normalized text and page metadata,
ready for the chunker.
"""

import logging
import re
from typing import TypedDict

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class ParsedPage(TypedDict):
    """Single page of extracted text with metadata."""
    text: str
    page_number: int | None


def _normalize_text(raw_text: str) -> str:
    """
    Clean up raw extracted text for downstream chunking/embedding.

    - Collapses 3+ consecutive newlines into 2 (preserves paragraph breaks)
    - Strips trailing whitespace from each line
    - Removes leading/trailing whitespace from the full text
    """
    # Strip trailing whitespace per line
    text = "\n".join(line.rstrip() for line in raw_text.splitlines())
    # Collapse excessive blank lines (3+ newlines → 2)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_text_file(file_bytes: bytes) -> list[ParsedPage]:
    """
    Parse a plain text file from raw bytes.

    Returns a single-element list with page_number=None (text files have no pages).
    Handles UTF-8 with BOM and replaces undecodable bytes.
    """
    # Strip UTF-8 BOM if present
    if file_bytes.startswith(b"\xef\xbb\xbf"):
        file_bytes = file_bytes[3:]

    text = file_bytes.decode("utf-8", errors="replace")
    normalized = _normalize_text(text)

    logger.info("Parsed text file: %d chars", len(normalized))
    return [ParsedPage(text=normalized, page_number=None)]


def parse_pdf(file_bytes: bytes) -> list[ParsedPage]:
    """
    Extract text from a PDF, one entry per non-blank page.

    Uses PyMuPDF for text extraction in reading-order mode.
    Handles corrupted files, encrypted/password-protected PDFs,
    and documents with zero extractable text.

    Raises:
        ValueError: If the PDF is encrypted/password-protected, corrupted,
                    or contains no extractable text.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        logger.error("Failed to open PDF: %s", exc)
        raise ValueError(
            f"Could not open PDF — the file may be corrupted or invalid: {exc}"
        ) from exc

    try:
        # Reject password-protected PDFs
        if doc.is_encrypted:
            raise ValueError(
                "PDF is password-protected. Please upload an unprotected PDF."
            )

        total_pages = len(doc)
        logger.info("Parsing PDF: %d total pages", total_pages)

        pages: list[ParsedPage] = []
        for page_num, page in enumerate(doc, start=1):
            raw_text = page.get_text("text")  # reading-order extraction
            normalized = _normalize_text(raw_text)

            if not normalized:
                logger.debug("Skipping blank page %d", page_num)
                continue

            pages.append(ParsedPage(text=normalized, page_number=page_num))

        if not pages:
            raise ValueError(
                "PDF contains no extractable text. "
                "It may be a scanned/image-only document."
            )

        logger.info(
            "PDF parsed: %d text pages extracted from %d total",
            len(pages), total_pages,
        )
        return pages

    finally:
        doc.close()


def parse_document(file_bytes: bytes, mime_type: str) -> list[ParsedPage]:
    """
    Route to the correct parser based on MIME type.

    Raises:
        ValueError: If the MIME type is unsupported, or the file cannot be parsed.
    """
    if mime_type == "application/pdf":
        return parse_pdf(file_bytes)
    elif mime_type == "text/plain":
        return parse_text_file(file_bytes)
    else:
        raise ValueError(f"Unsupported mime type: {mime_type}")

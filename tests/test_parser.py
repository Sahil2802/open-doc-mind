"""
Unit tests for backend.ingestion.parser.

Uses PyMuPDF (fitz) to generate real PDF bytes in-memory — no external
test fixture files required.
"""

import fitz  # PyMuPDF
import pytest

from backend.ingestion.parser import (
    ParsedPage,
    _normalize_text,
    parse_document,
    parse_pdf,
    parse_text_file,
)


# ---------------------------------------------------------------------------
# Helpers — build PDF bytes in memory
# ---------------------------------------------------------------------------

def _make_pdf(pages_text: list[str]) -> bytes:
    """Create a minimal PDF with the given text on each page."""
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_blank_pdf(num_pages: int = 1) -> bytes:
    """Create a PDF with only blank pages."""
    return _make_pdf([""] * num_pages)


# ---------------------------------------------------------------------------
# _normalize_text
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_collapses_excessive_newlines(self):
        assert _normalize_text("a\n\n\n\nb") == "a\n\nb"

    def test_preserves_double_newline(self):
        assert _normalize_text("a\n\nb") == "a\n\nb"

    def test_strips_trailing_whitespace_per_line(self):
        assert _normalize_text("hello   \nworld  ") == "hello\nworld"

    def test_strips_leading_trailing_whitespace(self):
        assert _normalize_text("  hello  ") == "hello"

    def test_empty_string(self):
        assert _normalize_text("") == ""


# ---------------------------------------------------------------------------
# parse_text_file
# ---------------------------------------------------------------------------

class TestParseTextFile:
    def test_basic_text(self):
        content = b"Hello, world!"
        result = parse_text_file(content)
        assert len(result) == 1
        assert result[0]["text"] == "Hello, world!"
        assert result[0]["page_number"] is None

    def test_utf8_with_bom(self):
        bom = b"\xef\xbb\xbf"
        content = bom + "Café résumé".encode("utf-8")
        result = parse_text_file(content)
        assert "Café résumé" in result[0]["text"]

    def test_invalid_bytes_replaced(self):
        content = b"Hello \xff world"
        result = parse_text_file(content)
        # \xff is not valid UTF-8, should be replaced with U+FFFD
        assert "\ufffd" in result[0]["text"]

    def test_empty_file(self):
        result = parse_text_file(b"")
        assert len(result) == 1
        assert result[0]["text"] == ""

    def test_normalizes_whitespace(self):
        content = b"para one\n\n\n\npara two"
        result = parse_text_file(content)
        assert result[0]["text"] == "para one\n\npara two"


# ---------------------------------------------------------------------------
# parse_pdf
# ---------------------------------------------------------------------------

class TestParsePdf:
    def test_single_page(self):
        pdf = _make_pdf(["Hello from page one"])
        result = parse_pdf(pdf)
        assert len(result) == 1
        assert "Hello from page one" in result[0]["text"]
        assert result[0]["page_number"] == 1

    def test_multi_page(self):
        pdf = _make_pdf(["Page A", "Page B", "Page C"])
        result = parse_pdf(pdf)
        assert len(result) == 3
        assert result[0]["page_number"] == 1
        assert result[1]["page_number"] == 2
        assert result[2]["page_number"] == 3

    def test_blank_pages_skipped(self):
        pdf = _make_pdf(["Content", "", "More content"])
        result = parse_pdf(pdf)
        assert len(result) == 2
        assert result[0]["page_number"] == 1
        assert result[1]["page_number"] == 3  # page 2 was blank

    def test_all_blank_raises(self):
        pdf = _make_blank_pdf(3)
        with pytest.raises(ValueError, match="no extractable text"):
            parse_pdf(pdf)

    def test_corrupted_bytes_raises(self):
        with pytest.raises(ValueError, match="corrupted or invalid"):
            parse_pdf(b"this is not a pdf at all")

    def test_text_is_normalized(self):
        # PyMuPDF may produce extra whitespace; verify normalization runs
        pdf = _make_pdf(["Line one\n\n\n\nLine two"])
        result = parse_pdf(pdf)
        # After normalization, 3+ newlines should collapse
        assert "\n\n\n" not in result[0]["text"]


# ---------------------------------------------------------------------------
# parse_document (router)
# ---------------------------------------------------------------------------

class TestParseDocument:
    def test_routes_text(self):
        result = parse_document(b"hello", "text/plain")
        assert len(result) == 1
        assert result[0]["page_number"] is None

    def test_routes_pdf(self):
        pdf = _make_pdf(["PDF content"])
        result = parse_document(pdf, "application/pdf")
        assert len(result) == 1
        assert result[0]["page_number"] == 1

    def test_unsupported_mime_raises(self):
        with pytest.raises(ValueError, match="Unsupported mime type"):
            parse_document(b"data", "image/png")

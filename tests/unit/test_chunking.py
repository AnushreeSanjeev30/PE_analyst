import pytest

from pe_analyst.document_intelligence.models import ExtractedPage
from pe_analyst.rag.chunking import DocumentChunker


def test_chunk_windows_long_page_text_with_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(200))
    pages = [ExtractedPage(1, text)]

    chunks = DocumentChunker().chunk("doc-1", pages, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert all(chunk.document_id == "doc-1" for chunk in chunks)
    assert all(len(chunk.text) <= 100 for chunk in chunks)
    # Consecutive chunks overlap: the tail of one reappears at the head of the next.
    assert chunks[0].text[-20:] in chunks[1].text


def test_chunk_returns_one_chunk_for_short_pages() -> None:
    pages = [ExtractedPage(1, "Short page text.")]

    chunks = DocumentChunker().chunk("doc-1", pages, chunk_size=1000, overlap=100)

    assert len(chunks) == 1
    assert chunks[0].text == "Short page text."


def test_chunk_skips_blank_pages() -> None:
    pages = [ExtractedPage(1, "   "), ExtractedPage(2, "Real content here.")]

    chunks = DocumentChunker().chunk("doc-1", pages, chunk_size=1000, overlap=100)

    assert len(chunks) == 1
    assert chunks[0].page_number == 2


def test_chunk_rejects_invalid_overlap() -> None:
    pages = [ExtractedPage(1, "text")]

    with pytest.raises(ValueError):
        DocumentChunker().chunk("doc-1", pages, chunk_size=100, overlap=100)

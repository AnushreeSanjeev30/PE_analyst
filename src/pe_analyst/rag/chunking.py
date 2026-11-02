"""Windows extracted page text into overlapping, citable chunks."""

from __future__ import annotations

from uuid import uuid4

from pe_analyst.document_intelligence.models import ExtractedPage

from .models import Chunk


class DocumentChunker:
    def chunk(
        self,
        document_id: str,
        pages: list[ExtractedPage],
        *,
        chunk_size: int,
        overlap: int,
    ) -> list[Chunk]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size")

        step = chunk_size - overlap
        chunks: list[Chunk] = []
        for page in pages:
            text = " ".join(page.text.split())
            if not text:
                continue
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunks.append(
                    Chunk(
                        id=str(uuid4()),
                        document_id=document_id,
                        page_number=page.page_number,
                        text=text[start:end],
                    )
                )
                if end == len(text):
                    break
                start += step
        return chunks


__all__ = ["DocumentChunker"]

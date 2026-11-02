"""Turns a PDF into searchable chunks, and questions into ranked, cited evidence."""

from __future__ import annotations

from pathlib import Path

from pe_analyst.core.config import Settings
from pe_analyst.document_intelligence.extractor import PDFExtractor
from pe_analyst.llm.factory import select_provider
from pe_analyst.llm.service import LLMService

from .chunking import DocumentChunker
from .embeddings import EmbeddingProvider, build_embedding_provider
from .models import RetrievedChunk
from .reranking import LLMReranker, Reranker, ScoreSliceReranker
from .vector_store import VectorStore, build_vector_store


class RetrievalService:
    def __init__(
        self,
        embeddings: EmbeddingProvider,
        store: VectorStore,
        settings: Settings,
        *,
        extractor: PDFExtractor | None = None,
        chunker: DocumentChunker | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.embeddings = embeddings
        self.store = store
        self.settings = settings
        self.extractor = extractor or PDFExtractor()
        self.chunker = chunker or DocumentChunker()
        self.reranker = reranker or ScoreSliceReranker()

    def ingest_document(self, path: str | Path, document_id: str) -> int:
        """Extract, chunk, embed, and store a PDF's pages. Returns the chunk count."""

        pdf = self.extractor.extract(Path(path))
        chunks = self.chunker.chunk(
            document_id,
            pdf.pages,
            chunk_size=self.settings.document_chunk_size,
            overlap=self.settings.document_chunk_overlap,
        )
        if not chunks:
            return 0
        vectors = self.embeddings.embed([chunk.text for chunk in chunks])
        self.store.add(chunks, vectors)
        return len(chunks)

    def retrieve(
        self, question: str, *, document_id: str | None = None, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        """Rank stored chunks against ``question``.

        With no explicit ``top_k``, retrieves ``settings.retrieval_top_k`` cosine-ranked
        candidates and reranks down to ``settings.rerank_top_k`` via ``self.reranker`` -- the
        LLM-scored ``LLMReranker`` when one was built with an available provider, otherwise a
        plain score-sorted slice.
        """

        vector = self.embeddings.embed([question])[0]
        if top_k is not None:
            return self.store.query(vector, top_k, document_id=document_id)
        retrieved = self.store.query(
            vector, self.settings.retrieval_top_k, document_id=document_id
        )
        return self.reranker.rerank(question, retrieved, self.settings.rerank_top_k)


def build_retrieval_service(
    settings: Settings, llm_service: LLMService | None = None
) -> RetrievalService:
    reranker: Reranker = ScoreSliceReranker()
    selected = select_provider(settings, llm_service) if llm_service is not None else None
    if llm_service is not None and selected is not None:
        reranker = LLMReranker(llm_service, provider=selected[0], model=selected[1])
    return RetrievalService(
        build_embedding_provider(settings),
        build_vector_store(settings),
        settings,
        reranker=reranker,
    )


__all__ = ["RetrievalService", "build_retrieval_service"]

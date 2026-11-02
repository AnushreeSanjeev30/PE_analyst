from pathlib import Path

from pe_analyst.core.config import Settings
from pe_analyst.document_intelligence.models import ExtractedPage, ExtractedPDF
from pe_analyst.llm.models import LLMProviderName
from pe_analyst.llm.service import LLMService
from pe_analyst.rag.embeddings import LocalHashingEmbeddingProvider
from pe_analyst.rag.reranking import LLMReranker, ScoreSliceReranker
from pe_analyst.rag.retrieval import RetrievalService, build_retrieval_service
from pe_analyst.rag.vector_store import LocalVectorStore


class FakeExtractor:
    def extract(self, path: Path) -> ExtractedPDF:
        return ExtractedPDF(
            path=path,
            page_count=2,
            pages=[
                ExtractedPage(1, "Revenue increased due to strong product demand this quarter."),
                ExtractedPage(
                    2, "Litigation risk includes an ongoing regulatory investigation."
                ),
            ],
        )


def _service(test_settings: Settings) -> RetrievalService:
    store = LocalVectorStore(test_settings.processed_data_dir / "vectors.json")
    return RetrievalService(
        LocalHashingEmbeddingProvider(), store, test_settings, extractor=FakeExtractor()
    )


def test_ingest_document_returns_the_chunk_count(test_settings: Settings) -> None:
    service = _service(test_settings)

    chunk_count = service.ingest_document("ExampleCo.pdf", "doc-1")

    assert chunk_count == 2


def test_retrieve_ranks_the_matching_chunk_first(test_settings: Settings) -> None:
    service = _service(test_settings)
    service.ingest_document("ExampleCo.pdf", "doc-1")

    results = service.retrieve("What drove revenue growth this quarter?")

    assert results[0].chunk.page_number == 1
    assert results[0].chunk.document_id == "doc-1"


def test_retrieve_respects_document_id_filter(test_settings: Settings) -> None:
    service = _service(test_settings)
    service.ingest_document("ExampleCo.pdf", "doc-1")
    service.ingest_document("OtherCo.pdf", "doc-2")

    results = service.retrieve("revenue", document_id="doc-2")

    assert all(item.chunk.document_id == "doc-2" for item in results)


def test_retrieve_honors_explicit_top_k(test_settings: Settings) -> None:
    service = _service(test_settings)
    service.ingest_document("ExampleCo.pdf", "doc-1")

    results = service.retrieve("revenue litigation", top_k=1)

    assert len(results) == 1


def test_build_retrieval_service_defaults_to_score_slice_reranker(test_settings: Settings) -> None:
    service = build_retrieval_service(test_settings)

    assert isinstance(service.reranker, ScoreSliceReranker)


def test_build_retrieval_service_uses_llm_reranker_when_openai_is_available(
    test_settings: Settings,
) -> None:
    class _StubProvider:
        name = LLMProviderName.OPENAI

        def generate(self, request):  # type: ignore[no-untyped-def]
            raise AssertionError("not called in this test")

    llm_service = LLMService({LLMProviderName.OPENAI: _StubProvider()})

    service = build_retrieval_service(test_settings, llm_service)

    assert isinstance(service.reranker, LLMReranker)

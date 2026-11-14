from pe_analyst.llm.exceptions import LLMProviderError
from pe_analyst.llm.models import LLMProviderName, LLMRequest, LLMResponse
from pe_analyst.llm.service import LLMService
from pe_analyst.rag.answering import RAGService
from pe_analyst.rag.models import Chunk, RetrievedChunk


class FakeRetrieval:
    def __init__(self, results: list[RetrievedChunk]) -> None:
        self.results = results
        self.last_call: dict[str, object] | None = None

    def retrieve(self, question: str, *, document_id: str | None = None) -> list[RetrievedChunk]:
        self.last_call = {"question": question, "document_id": document_id}
        return self.results


class FakeLLMProvider:
    name = LLMProviderName.OPENAI

    def __init__(self) -> None:
        self.last_request: LLMRequest | None = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(
            "Revenue grew because of strong demand (Page 1).", self.name, request.model
        )


def _chunk_result(page: int, text: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(Chunk("id", "doc-1", page, text), score)


class _BrokenRetrieval:
    def retrieve(self, question: str, *, document_id: str | None = None) -> list[RetrievedChunk]:
        raise RuntimeError("embedding provider returned 401")


def test_answer_degrades_gracefully_when_retrieval_raises() -> None:
    service = RAGService(_BrokenRetrieval())

    result = service.answer("What is the EBITDA margin?")

    assert result.confidence == 0.0
    assert result.citations == []
    assert "embedding provider returned 401" in result.warnings[0]


def test_answer_with_no_evidence_never_fabricates() -> None:
    service = RAGService(FakeRetrieval([]))

    result = service.answer("What is the EBITDA margin?")

    assert result.confidence == 0.0
    assert result.citations == []
    assert result.warnings


def test_answer_uses_the_llm_when_a_provider_is_configured() -> None:
    provider = FakeLLMProvider()
    llm_service = LLMService({LLMProviderName.OPENAI: provider})
    retrieval = FakeRetrieval([_chunk_result(1, "Revenue increased due to demand.", 0.9)])
    service = RAGService(
        retrieval, llm_service, provider=LLMProviderName.OPENAI, model="gpt-5-mini"
    )

    result = service.answer("Why did revenue grow?")

    assert "Revenue grew" in result.answer
    assert provider.last_request is not None
    assert "Revenue increased due to demand." in provider.last_request.messages[0].content
    assert result.citations[0].page_number == 1
    assert not result.warnings


def test_answer_falls_back_to_excerpts_without_an_llm_provider() -> None:
    retrieval = FakeRetrieval([_chunk_result(2, "Litigation risk noted.", 0.8)])
    service = RAGService(retrieval, llm_service=None)

    result = service.answer("What are the risks?")

    assert "Litigation risk noted." in result.answer
    assert result.warnings
    assert result.confidence < 0.8


def test_answer_falls_back_when_requested_provider_is_not_registered() -> None:
    llm_service = LLMService({})
    retrieval = FakeRetrieval([_chunk_result(1, "Some evidence.", 0.5)])
    service = RAGService(
        retrieval, llm_service, provider=LLMProviderName.OPENAI, model="gpt-5-mini"
    )

    result = service.answer("Question?")

    assert "Some evidence." in result.answer
    assert result.warnings


class _RateLimitedProvider:
    name = LLMProviderName.OPENAI

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise LLMProviderError("Provider request failed: 429 rate limit reached")


def test_answer_falls_back_to_excerpts_when_the_llm_is_rate_limited() -> None:
    """Regression: a 429 from the provider used to surface as a 500 from /rag/query."""

    llm_service = LLMService({LLMProviderName.OPENAI: _RateLimitedProvider()})
    retrieval = FakeRetrieval([_chunk_result(4, "Top customer is 30% of revenue.", 0.8)])
    service = RAGService(
        retrieval, llm_service, provider=LLMProviderName.OPENAI, model="gpt-5-mini"
    )

    result = service.answer("How concentrated are customers?")

    assert "Top customer is 30% of revenue." in result.answer
    assert result.citations[0].page_number == 4
    assert "429" in result.warnings[0]

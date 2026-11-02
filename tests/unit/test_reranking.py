import json

from pe_analyst.llm.models import LLMProviderName, LLMRequest, LLMResponse
from pe_analyst.llm.service import LLMService
from pe_analyst.rag.models import Chunk, RetrievedChunk
from pe_analyst.rag.reranking import LLMReranker, ScoreSliceReranker


def _candidate(chunk_id: str, page: int, text: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(Chunk(chunk_id, "doc-1", page, text), score)


def test_score_slice_reranker_keeps_existing_order_and_slices() -> None:
    candidates = [_candidate("a", 1, "x", 0.9), _candidate("b", 2, "y", 0.5)]

    result = ScoreSliceReranker().rerank("question", candidates, 1)

    assert [item.chunk.id for item in result] == ["a"]


class _FakeProvider:
    name = LLMProviderName.OPENAI

    def __init__(self, scores: dict[int, float]) -> None:
        self.scores = scores

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "scores": [
                {"index": index, "relevance": relevance} for index, relevance in self.scores.items()
            ]
        }
        return LLMResponse(json.dumps(payload), self.name, request.model)


def test_llm_reranker_reorders_by_model_relevance_scores() -> None:
    provider = _FakeProvider({0: 0.2, 1: 0.9})
    llm_service = LLMService({LLMProviderName.OPENAI: provider})
    candidates = [_candidate("low", 1, "irrelevant", 0.9), _candidate("high", 2, "relevant", 0.5)]
    reranker = LLMReranker(llm_service, provider=LLMProviderName.OPENAI, model="gpt-5-mini")

    result = reranker.rerank("question", candidates, 2)

    assert [item.chunk.id for item in result] == ["high", "low"]


def test_llm_reranker_falls_back_on_malformed_response() -> None:
    class _BrokenProvider:
        name = LLMProviderName.OPENAI

        def generate(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse("not json", self.name, request.model)

    llm_service = LLMService({LLMProviderName.OPENAI: _BrokenProvider()})
    candidates = [_candidate("a", 1, "x", 0.9), _candidate("b", 2, "y", 0.5)]
    reranker = LLMReranker(llm_service, provider=LLMProviderName.OPENAI, model="gpt-5-mini")

    result = reranker.rerank("question", candidates, 2)

    assert [item.chunk.id for item in result] == ["a", "b"]


def test_llm_reranker_falls_back_when_provider_raises() -> None:
    class _RaisingProvider:
        name = LLMProviderName.OPENAI

        def generate(self, request: LLMRequest) -> LLMResponse:
            raise RuntimeError("provider unavailable")

    llm_service = LLMService({LLMProviderName.OPENAI: _RaisingProvider()})
    candidates = [_candidate("a", 1, "x", 0.9), _candidate("b", 2, "y", 0.5)]
    reranker = LLMReranker(llm_service, provider=LLMProviderName.OPENAI, model="gpt-5-mini")

    result = reranker.rerank("question", candidates, 1)

    assert [item.chunk.id for item in result] == ["a"]


def test_llm_reranker_handles_empty_candidates() -> None:
    llm_service = LLMService({})
    reranker = LLMReranker(llm_service, provider=LLMProviderName.OPENAI, model="gpt-5-mini")

    assert reranker.rerank("question", [], 5) == []

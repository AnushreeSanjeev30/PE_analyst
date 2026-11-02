"""Reranking: today's cosine-sorted slice, or a real LLM-as-reranker when a provider exists.

The LLM reranker asks the model to score each retrieval candidate's relevance to the question
via a JSON-schema-constrained response, then sorts by that score. Any provider failure or
malformed response falls back to the plain cosine slice -- the same
never-break-the-primary-path rule used throughout the rest of this codebase.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from pe_analyst.llm.models import LLMMessage, LLMProviderName, LLMRequest
from pe_analyst.llm.service import LLMService

from .models import RetrievedChunk

_RERANK_SYSTEM_PROMPT = (
    "You score how relevant each excerpt is to a question, on a 0.0-1.0 scale. Respond only "
    "with the requested JSON."
)

_RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "relevance": {"type": "number"},
                },
                "required": ["index", "relevance"],
            },
        }
    },
    "required": ["scores"],
}


class Reranker(ABC):
    @abstractmethod
    def rerank(
        self, question: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]: ...


class ScoreSliceReranker(Reranker):
    """Today's behavior: keep the cosine-similarity ranking, just slice to top_k."""

    def rerank(
        self, question: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        return candidates[:top_k]


class LLMReranker(Reranker):
    def __init__(
        self,
        llm_service: LLMService,
        *,
        provider: LLMProviderName = LLMProviderName.OPENAI,
        model: str,
    ) -> None:
        self.llm_service = llm_service
        self.provider = provider
        self.model = model
        self._fallback = ScoreSliceReranker()

    def rerank(
        self, question: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        try:
            scores = self._score(question, candidates)
        except Exception:  # noqa: BLE001 - any provider/parsing failure falls back
            return self._fallback.rerank(question, candidates, top_k)
        if len(scores) != len(candidates):
            return self._fallback.rerank(question, candidates, top_k)
        ranked = sorted(
            zip(candidates, scores, strict=True), key=lambda pair: pair[1], reverse=True
        )
        return [candidate for candidate, _ in ranked[:top_k]]

    def _score(self, question: str, candidates: list[RetrievedChunk]) -> list[float]:
        excerpts = "\n\n".join(
            f"[{index}] {item.chunk.text}" for index, item in enumerate(candidates)
        )
        request = LLMRequest(
            messages=[
                LLMMessage(
                    "user",
                    f"Question: {question}\n\nExcerpts:\n{excerpts}\n\n"
                    f"Score every excerpt index 0-{len(candidates) - 1}.",
                )
            ],
            model=self.model,
            system_prompt=_RERANK_SYSTEM_PROMPT,
            response_schema=_RERANK_SCHEMA,
        )
        response = self.llm_service.generate(self.provider, request)
        payload = json.loads(response.text)
        by_index = {int(item["index"]): float(item["relevance"]) for item in payload["scores"]}
        return [by_index[index] for index in range(len(candidates))]


__all__ = ["LLMReranker", "Reranker", "ScoreSliceReranker"]

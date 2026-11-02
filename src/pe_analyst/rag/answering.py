"""Synthesizes a grounded, cited answer from retrieved chunks -- or discloses that it can't.

Mirrors the rest of the underwriting stack's control principle: the retrieval step is the source
of truth for *what evidence exists*, and the LLM (when one is configured) only explains that
evidence -- it never answers from anything but the supplied excerpts, and a missing provider
degrades to returning the excerpts directly rather than failing or guessing.
"""

from __future__ import annotations

from pe_analyst.core.config import Settings
from pe_analyst.llm.factory import select_provider
from pe_analyst.llm.models import LLMMessage, LLMProviderName, LLMRequest
from pe_analyst.llm.service import LLMService

from .models import Citation, RAGAnswer, RetrievedChunk
from .retrieval import RetrievalService, build_retrieval_service

_SYSTEM_PROMPT = (
    "Answer strictly using the numbered page excerpts provided. Cite page numbers inline. "
    "If the excerpts do not contain enough information to answer, say so explicitly instead "
    "of guessing."
)


class RAGService:
    def __init__(
        self,
        retrieval: RetrievalService,
        llm_service: LLMService | None = None,
        *,
        provider: LLMProviderName = LLMProviderName.OPENAI,
        model: str | None = None,
    ) -> None:
        self.retrieval = retrieval
        self.llm_service = llm_service
        self.provider = provider
        self.model = model

    def answer(self, question: str, *, document_id: str | None = None) -> RAGAnswer:
        try:
            retrieved = self.retrieval.retrieve(question, document_id=document_id)
        except Exception as error:  # noqa: BLE001 - a broken embedding/store call must not 500
            return RAGAnswer(
                answer="Retrieval is currently unavailable; no answer could be produced.",
                citations=[],
                confidence=0.0,
                warnings=[f"Retrieval failed: {error}"],
            )
        if not retrieved:
            return RAGAnswer(
                answer="No relevant evidence was found for this question.",
                citations=[],
                confidence=0.0,
                warnings=["No indexed content matched the question."],
            )

        citations = [
            Citation(
                item.chunk.document_id, item.chunk.page_number, item.chunk.text[:500], item.score
            )
            for item in retrieved
        ]
        confidence = max(0.0, min(1.0, sum(item.score for item in retrieved) / len(retrieved)))

        if (
            self.llm_service is not None
            and self.model
            and self.provider in self.llm_service.providers
        ):
            request = LLMRequest(
                messages=[LLMMessage("user", self._prompt(question, retrieved))],
                model=self.model,
                system_prompt=_SYSTEM_PROMPT,
            )
            response = self.llm_service.generate(self.provider, request)
            return RAGAnswer(response.text.strip(), citations, confidence, [])

        return RAGAnswer(
            self._fallback_answer(retrieved),
            citations,
            confidence * 0.5,
            [
                "No LLM provider is configured; returning the top matching excerpts instead of "
                "a synthesized answer."
            ],
        )

    @staticmethod
    def _prompt(question: str, retrieved: list[RetrievedChunk]) -> str:
        excerpts = "\n\n".join(
            f"[Page {item.chunk.page_number}] {item.chunk.text}" for item in retrieved
        )
        return f"Question: {question}\n\nExcerpts:\n{excerpts}"

    @staticmethod
    def _fallback_answer(retrieved: list[RetrievedChunk]) -> str:
        return "\n\n".join(
            f"(Page {item.chunk.page_number}) {item.chunk.text}" for item in retrieved
        )


def build_rag_service(settings: Settings, llm_service: LLMService | None = None) -> RAGService:
    selected = select_provider(settings, llm_service) if llm_service is not None else None
    provider, model = selected if selected is not None else (LLMProviderName.OPENAI, None)
    return RAGService(
        build_retrieval_service(settings, llm_service),
        llm_service,
        provider=provider,
        model=model,
    )


__all__ = ["RAGService", "build_rag_service"]

"""API-boundary contracts for retrieval-augmented answers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .models import RAGAnswer


class CitationSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    page_number: int = Field(ge=1)
    excerpt: str
    score: float


class RAGAnswerSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    citations: list[CitationSchema]
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str]

    @classmethod
    def from_result(cls, result: RAGAnswer) -> RAGAnswerSchema:
        return cls(
            answer=result.answer,
            citations=[
                CitationSchema(
                    document_id=citation.document_id,
                    page_number=citation.page_number,
                    excerpt=citation.excerpt,
                    score=citation.score,
                )
                for citation in result.citations
            ],
            confidence=result.confidence,
            warnings=result.warnings,
        )


class RAGQueryRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: str | None = None


__all__ = ["CitationSchema", "RAGAnswerSchema", "RAGQueryRequest"]

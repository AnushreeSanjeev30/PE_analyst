"""Contracts shared across chunking, retrieval, and answer synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Chunk:
    id: str
    document_id: str
    page_number: int
    text: str


@dataclass(slots=True, frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


@dataclass(slots=True, frozen=True)
class Citation:
    document_id: str
    page_number: int
    excerpt: str
    score: float


@dataclass(slots=True, frozen=True)
class RAGAnswer:
    answer: str
    citations: list[Citation]
    confidence: float
    warnings: list[str] = field(default_factory=list)


__all__ = ["Chunk", "Citation", "RAGAnswer", "RetrievedChunk"]

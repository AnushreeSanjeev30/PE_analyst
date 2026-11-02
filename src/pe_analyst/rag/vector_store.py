"""A pluggable vector store, with a local file-backed default.

No Postgres/pgvector infrastructure exists yet (that's Phase 12), so ``LocalVectorStore`` is the
only implementation today. It stores everything in one JSON file and does a linear cosine-similarity
scan on query -- fine at the scale of a handful of deal documents. A future ``PgVectorStore`` can
implement the same :class:`VectorStore` interface without touching any caller.
"""

from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pe_analyst.core.config import Settings

from .models import Chunk, RetrievedChunk


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    @abstractmethod
    def query(
        self, vector: list[float], top_k: int, *, document_id: str | None = None
    ) -> list[RetrievedChunk]: ...


class LocalVectorStore(VectorStore):
    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        return list(json.loads(self.path.read_text(encoding="utf-8")))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._records), encoding="utf-8")

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        for chunk, vector in zip(chunks, vectors, strict=True):
            self._records.append(
                {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "page_number": chunk.page_number,
                    "text": chunk.text,
                    "vector": vector,
                }
            )
        self._save()

    def query(
        self, vector: list[float], top_k: int, *, document_id: str | None = None
    ) -> list[RetrievedChunk]:
        candidates = (
            self._records
            if document_id is None
            else [record for record in self._records if record["document_id"] == document_id]
        )
        scored = [
            RetrievedChunk(
                Chunk(record["id"], record["document_id"], record["page_number"], record["text"]),
                self._cosine_similarity(vector, record["vector"]),
            )
            for record in candidates
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return dot / (left_norm * right_norm)


def build_vector_store(settings: Settings) -> VectorStore:
    """Dispatch on ``settings.vector_store_provider``.

    ``"pgvector"`` is lazy-imported so the default local/offline path never has to import
    SQLAlchemy or open a database connection.
    """

    if settings.vector_store_provider == "pgvector":
        from .pgvector_store import PgVectorStore

        return PgVectorStore(settings)
    path = settings.processed_data_dir / "vectors" / f"{settings.vector_collection_name}.json"
    return LocalVectorStore(path)


__all__ = ["LocalVectorStore", "VectorStore", "build_vector_store"]

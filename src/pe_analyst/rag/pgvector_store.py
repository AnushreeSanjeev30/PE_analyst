"""Postgres+pgvector-backed :class:`VectorStore`, selected via VECTOR_STORE_PROVIDER=pgvector."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from pe_analyst.core.config import Settings
from pe_analyst.db.models import VectorChunkModel
from pe_analyst.db.session import get_engine

from .models import Chunk, RetrievedChunk
from .vector_store import VectorStore


class PgVectorStore(VectorStore):
    def __init__(self, settings: Settings) -> None:
        self._engine = get_engine(settings)

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        with Session(self._engine) as session:
            for chunk, vector in zip(chunks, vectors, strict=True):
                session.add(
                    VectorChunkModel(
                        id=chunk.id,
                        document_id=chunk.document_id,
                        page_number=chunk.page_number,
                        text=chunk.text,
                        embedding=vector,
                    )
                )
            session.commit()

    def query(
        self, vector: list[float], top_k: int, *, document_id: str | None = None
    ) -> list[RetrievedChunk]:
        distance = VectorChunkModel.embedding.cosine_distance(vector)
        statement = select(VectorChunkModel, distance.label("distance")).order_by(distance)
        if document_id is not None:
            statement = statement.where(VectorChunkModel.document_id == document_id)
        statement = statement.limit(top_k)

        with Session(self._engine) as session:
            rows = session.execute(statement).all()

        return [
            RetrievedChunk(
                Chunk(record.id, record.document_id, record.page_number, record.text),
                1.0 - float(distance_value),
            )
            for record, distance_value in rows
        ]


__all__ = ["PgVectorStore"]

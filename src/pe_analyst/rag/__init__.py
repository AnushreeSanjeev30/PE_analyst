"""Chunking, embedding, and retrieval-augmented answering over ingested documents."""

from __future__ import annotations

from .answering import RAGService, build_rag_service
from .embeddings import (
    EmbeddingProvider,
    LocalHashingEmbeddingProvider,
    OpenAIEmbeddingProvider,
    build_embedding_provider,
)
from .models import Chunk, Citation, RAGAnswer, RetrievedChunk
from .reranking import LLMReranker, Reranker, ScoreSliceReranker
from .retrieval import RetrievalService, build_retrieval_service
from .vector_store import LocalVectorStore, VectorStore, build_vector_store

__all__ = [
    "Chunk",
    "Citation",
    "EmbeddingProvider",
    "LLMReranker",
    "LocalHashingEmbeddingProvider",
    "LocalVectorStore",
    "OpenAIEmbeddingProvider",
    "RAGAnswer",
    "RAGService",
    "Reranker",
    "RetrievalService",
    "RetrievedChunk",
    "ScoreSliceReranker",
    "VectorStore",
    "build_embedding_provider",
    "build_rag_service",
    "build_retrieval_service",
    "build_vector_store",
]

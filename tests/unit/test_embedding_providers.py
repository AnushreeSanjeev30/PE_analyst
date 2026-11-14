"""Embedding provider selection, the Gemini request shape, and document-scoped search."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from pe_analyst.core.config import Settings
from pe_analyst.rag.embeddings import (
    GeminiEmbeddingProvider,
    LocalHashingEmbeddingProvider,
    OpenAIEmbeddingProvider,
    build_embedding_provider,
)
from pe_analyst.rag.exceptions import EmbeddingConfigurationError, EmbeddingProviderError
from pe_analyst.rag.models import Chunk
from pe_analyst.rag.vector_store import LocalVectorStore


def test_auto_prefers_openai_then_gemini_then_local(test_settings: Settings) -> None:
    both = test_settings.model_copy(update={"openai_api_key": "sk", "gemini_api_key": "g"})
    gemini_only = test_settings.model_copy(update={"gemini_api_key": "g"})

    assert isinstance(build_embedding_provider(both), OpenAIEmbeddingProvider)
    assert isinstance(build_embedding_provider(gemini_only), GeminiEmbeddingProvider)
    assert isinstance(build_embedding_provider(test_settings), LocalHashingEmbeddingProvider)


def test_local_can_be_forced_even_with_keys_present(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={"openai_api_key": "sk", "embedding_provider": "local"}
    )

    assert isinstance(build_embedding_provider(settings), LocalHashingEmbeddingProvider)


def test_naming_a_provider_without_its_key_is_an_error(test_settings: Settings) -> None:
    settings = test_settings.model_copy(update={"embedding_provider": "gemini"})

    with pytest.raises(EmbeddingConfigurationError, match="GEMINI_API_KEY"):
        build_embedding_provider(settings)


def test_unknown_provider_name_is_an_error(test_settings: Settings) -> None:
    settings = test_settings.model_copy(update={"embedding_provider": "cohere"})

    with pytest.raises(EmbeddingConfigurationError, match="Unknown EMBEDDING_PROVIDER"):
        build_embedding_provider(settings)


def test_local_embedder_matches_the_pgvector_column_width(test_settings: Settings) -> None:
    """Regression: 256-wide local vectors could not be stored in the 1536-wide pgvector column,
    so with Docker and no embedding key every document silently failed to index."""

    settings = test_settings.model_copy(update={"vector_store_provider": "pgvector"})

    provider = build_embedding_provider(settings)

    assert len(provider.embed(["revenue growth"])[0]) == settings.embedding_dimension


def _gemini(handler: httpx.MockTransport) -> GeminiEmbeddingProvider:
    provider = GeminiEmbeddingProvider("key", "gemini-embedding-001", 8)
    provider.client = httpx.Client(
        base_url="https://generativelanguage.googleapis.com/v1beta", transport=handler
    )
    return provider


def test_gemini_batches_requests_and_returns_vectors_in_order() -> None:
    calls: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        assert request.url.path.endswith("/models/gemini-embedding-001:batchEmbedContents")
        assert all(item["outputDimensionality"] == 8 for item in body["requests"])
        calls.append(len(body["requests"]))
        return httpx.Response(
            200,
            json={
                "embeddings": [
                    {"values": [float(len(item["content"]["parts"][0]["text"]))] * 8}
                    for item in body["requests"]
                ]
            },
        )

    texts = ["a" * (index % 7 + 1) for index in range(150)]

    vectors = _gemini(httpx.MockTransport(handle)).embed(texts)

    assert calls == [100, 50]
    assert [vector[0] for vector in vectors] == [float(len(text)) for text in texts]


def test_gemini_failure_surfaces_as_a_provider_error() -> None:
    provider = _gemini(httpx.MockTransport(lambda request: httpx.Response(429, text="quota")))

    with pytest.raises(EmbeddingProviderError, match="429"):
        provider.embed(["hello"])


def test_local_store_restricts_search_to_a_set_of_documents(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    store.add(
        [Chunk("1", "mine", 1, "a"), Chunk("2", "theirs", 1, "b"), Chunk("3", "mine-too", 1, "c")],
        [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
    )

    allowed = store.query([1.0, 0.0], top_k=10, document_ids=["mine", "mine-too"])
    nothing = store.query([1.0, 0.0], top_k=10, document_ids=[])

    assert {item.chunk.document_id for item in allowed} == {"mine", "mine-too"}
    assert nothing == []

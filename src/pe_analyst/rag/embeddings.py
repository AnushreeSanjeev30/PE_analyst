"""Text-to-vector providers: OpenAI or Gemini when configured, a local fallback otherwise."""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

import httpx

from pe_analyst.core.config import Settings

from .exceptions import EmbeddingConfigurationError, EmbeddingProviderError

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None, model: str, timeout_seconds: float = 60.0) -> None:
        if not api_key:
            raise EmbeddingConfigurationError("OPENAI_API_KEY is not configured")
        self.model = model
        self.client = httpx.Client(
            base_url="https://api.openai.com/v1",
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.post("/embeddings", json={"model": self.model, "input": texts})
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise EmbeddingProviderError(
                f"Embedding request failed: {error.response.status_code} {error.response.text}"
            ) from error
        body = response.json()
        return [item["embedding"] for item in body["data"]]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini embeddings. The API has a free tier, so this is the no-cost upgrade over
    the local hashing fallback."""

    _BATCH_SIZE = 100  # batchEmbedContents accepts at most 100 texts per call

    def __init__(
        self,
        api_key: str | None,
        model: str,
        dimension: int,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not api_key:
            raise EmbeddingConfigurationError("GEMINI_API_KEY is not configured")
        self.model = model
        self.dimension = dimension
        self.client = httpx.Client(
            base_url="https://generativelanguage.googleapis.com/v1beta",
            timeout=timeout_seconds,
            headers={"x-goog-api-key": api_key},
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._BATCH_SIZE):
            vectors.extend(self._embed_batch(texts[start : start + self._BATCH_SIZE]))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    # The API rejects empty content; a single space embeds to a neutral vector.
                    "content": {"parts": [{"text": text or " "}]},
                    "outputDimensionality": self.dimension,
                }
                for text in texts
            ]
        }
        response = self.client.post(f"/models/{self.model}:batchEmbedContents", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise EmbeddingProviderError(
                f"Embedding request failed: {error.response.status_code} {error.response.text}"
            ) from error
        return [item["values"] for item in response.json()["embeddings"]]


class LocalHashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic feature-hashing embedder requiring no network access or API key.

    Tokens are hashed into a fixed-width vector (the classic "hashing trick") so semantically
    identical wording maps close together via cosine similarity, without needing a real model.
    Good enough for offline development and tests; not a substitute for a real embedding model.
    """

    dimension = 256

    def __init__(self, dimension: int | None = None) -> None:
        if dimension is not None:
            self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in _TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Pick the embedder named by ``EMBEDDING_PROVIDER`` (default ``auto``).

    ``auto`` mirrors ``llm.factory.build_llm_service``: a provider only activates when its
    credentials are present -- OpenAI first, then Gemini, then the offline local embedder -- so
    ingestion and retrieval keep working with zero external configuration. Naming a provider
    explicitly makes a missing key an error instead of a silent downgrade.

    Vectors from different providers are not comparable. After switching provider, documents
    must be uploaded again to be searchable.
    """

    choice = settings.embedding_provider.strip().lower()
    if choice not in {"auto", "openai", "gemini", "local"}:
        raise EmbeddingConfigurationError(
            f"Unknown EMBEDDING_PROVIDER '{settings.embedding_provider}'. "
            "Expected one of: auto, openai, gemini, local."
        )

    if choice == "openai" or (choice == "auto" and settings.openai_api_key):
        return OpenAIEmbeddingProvider(
            settings.openai_api_key, settings.openai_embedding_model, settings.llm_timeout_seconds
        )
    if choice == "gemini" or (choice == "auto" and settings.gemini_api_key):
        return GeminiEmbeddingProvider(
            settings.gemini_api_key,
            settings.gemini_embedding_model,
            settings.embedding_dimension,
            settings.llm_timeout_seconds,
        )
    # The pgvector column has a fixed width (EMBEDDING_DIMENSION); the local file store does not.
    if settings.vector_store_provider == "pgvector":
        return LocalHashingEmbeddingProvider(settings.embedding_dimension)
    return LocalHashingEmbeddingProvider()


__all__ = [
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "LocalHashingEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "build_embedding_provider",
]

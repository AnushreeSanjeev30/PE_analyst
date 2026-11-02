"""Text-to-vector providers: OpenAI when configured, a deterministic local fallback otherwise."""

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


class LocalHashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic feature-hashing embedder requiring no network access or API key.

    Tokens are hashed into a fixed-width vector (the classic "hashing trick") so semantically
    identical wording maps close together via cosine similarity, without needing a real model.
    Good enough for offline development and tests; not a substitute for a real embedding model.
    """

    dimension = 256

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
    """Use OpenAI when an API key is configured, otherwise the offline local embedder.

    Mirrors ``llm.factory.build_llm_service``: providers only activate when their credentials
    are present, so ingestion and retrieval keep working with zero external configuration.
    """

    if settings.openai_api_key:
        return OpenAIEmbeddingProvider(
            settings.openai_api_key, settings.openai_embedding_model, settings.llm_timeout_seconds
        )
    return LocalHashingEmbeddingProvider()


__all__ = [
    "EmbeddingProvider",
    "LocalHashingEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "build_embedding_provider",
]

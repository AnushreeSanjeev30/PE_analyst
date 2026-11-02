"""Errors raised by embedding providers."""

from __future__ import annotations


class EmbeddingConfigurationError(RuntimeError):
    """Raised when a provider is used without the credentials it requires."""


class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider's request fails."""


__all__ = ["EmbeddingConfigurationError", "EmbeddingProviderError"]

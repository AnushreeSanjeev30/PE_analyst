"""Errors raised by market-data providers."""

from __future__ import annotations


class MarketDataProviderError(RuntimeError):
    """Raised when market data can't be retrieved -- including "no vendor configured"."""


__all__ = ["MarketDataProviderError"]

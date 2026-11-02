"""Settings-based construction of the configured market-data provider."""

from __future__ import annotations

from pe_analyst.core.config import Settings

from .alphavantage import AlphaVantageMarketDataProvider
from .exceptions import MarketDataProviderError
from .provider import MarketDataProvider
from .unconfigured import UnconfiguredMarketDataProvider


def build_market_data_provider(settings: Settings) -> MarketDataProvider:
    name = settings.market_data_provider.lower()
    if name == "unconfigured":
        return UnconfiguredMarketDataProvider()
    if name == "alphavantage":
        return AlphaVantageMarketDataProvider(
            settings.market_data_api_key,
            cache_dir=settings.market_data_cache_dir,
            cache_ttl_hours=settings.market_data_cache_ttl_hours,
        )
    raise MarketDataProviderError(
        f"Unknown MARKET_DATA_PROVIDER={settings.market_data_provider!r}; "
        "expected 'unconfigured' or 'alphavantage'"
    )


__all__ = ["build_market_data_provider"]

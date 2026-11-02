"""Default provider: names what's missing instead of returning fabricated data."""

from __future__ import annotations

from pe_analyst.valuation.peer import PeerCompany

from .exceptions import MarketDataProviderError
from .provider import MarketDataProvider


class UnconfiguredMarketDataProvider(MarketDataProvider):
    def get_comparable_companies(self, industry_or_ticker: str) -> list[PeerCompany]:
        raise MarketDataProviderError(
            "No market-data vendor is configured (MARKET_DATA_PROVIDER=unconfigured). "
            "Supply comparable peers manually in valuation_inputs, or set "
            "MARKET_DATA_PROVIDER=alphavantage with a free MARKET_DATA_API_KEY."
        )


__all__ = ["UnconfiguredMarketDataProvider"]

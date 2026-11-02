"""The seam a licensed market-data vendor integration plugs into.

Return type reuses :class:`pe_analyst.valuation.peer.PeerCompany` -- the shape
``ValuationAgent``'s comparable-company analysis already consumes -- so a real implementation is
a drop-in for that analysis with no changes needed on the consuming side.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pe_analyst.valuation.peer import PeerCompany


class MarketDataProvider(ABC):
    @abstractmethod
    def get_comparable_companies(self, industry_or_ticker: str) -> list[PeerCompany]: ...


__all__ = ["MarketDataProvider"]

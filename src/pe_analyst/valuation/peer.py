from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PeerCompany:
    """
    Represents a comparable public company.
    """

    name: str

    enterprise_value: float

    market_cap: float

    revenue: float

    ebitda: float

    net_income: float

    book_value: float

    @property
    def ev_revenue(self) -> float:
        return self.enterprise_value / self.revenue if self.revenue > 0 else 0.0

    @property
    def ev_ebitda(self) -> float:
        return self.enterprise_value / self.ebitda if self.ebitda > 0 else 0.0

    @property
    def pe(self) -> float:
        return self.market_cap / self.net_income if self.net_income > 0 else 0.0

    @property
    def price_to_book(self) -> float:
        return self.market_cap / self.book_value if self.book_value > 0 else 0.0

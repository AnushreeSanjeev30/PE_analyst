from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ComparableStatistics:
    mean: float

    median: float

    minimum: float

    maximum: float

    percentile_25: float

    percentile_75: float


@dataclass(slots=True)
class ComparableValuationReport:
    peer_count: int

    ev_ebitda: ComparableStatistics

    ev_revenue: ComparableStatistics

    pe: ComparableStatistics

    price_to_book: ComparableStatistics

    implied_enterprise_value: float

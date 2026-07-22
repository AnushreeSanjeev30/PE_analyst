from __future__ import annotations

from statistics import mean, median


class StatisticsEngine:
    """
    Utility class for valuation statistics.
    """

    @staticmethod
    def mean(values: list[float]) -> float:
        return mean(values) if values else 0.0

    @staticmethod
    def median(values: list[float]) -> float:
        return median(values) if values else 0.0

    @staticmethod
    def minimum(values: list[float]) -> float:
        return min(values) if values else 0.0

    @staticmethod
    def maximum(values: list[float]) -> float:
        return max(values) if values else 0.0

    @staticmethod
    def percentile(values: list[float], percentile: float) -> float:
        """
        Linear interpolation percentile.
        """

        if not values:
            return 0.0

        values = sorted(values)

        k = (len(values) - 1) * percentile

        f = int(k)

        c = min(f + 1, len(values) - 1)

        if f == c:
            return values[f]

        d = k - f

        return values[f] * (1 - d) + values[c] * d

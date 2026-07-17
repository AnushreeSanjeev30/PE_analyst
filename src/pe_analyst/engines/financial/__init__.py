"""Financial analysis engine."""

from .growth import average_growth, cagr, growth_rate, project_value
from .models import FinancialStatement, GrowthMetrics
from .ratios import (
    asset_turnover,
    current_ratio,
    debt_to_ebitda,
    ebitda_margin,
    gross_margin,
    interest_coverage,
    net_margin,
    quick_ratio,
    return_on_assets,
    return_on_equity,
)

__all__ = [
    "asset_turnover",
    "current_ratio",
    "quick_ratio",
    "gross_margin",
    "ebitda_margin",
    "net_margin",
    "return_on_assets",
    "return_on_equity",
    "debt_to_ebitda",
    "interest_coverage",
    "FinancialStatement",
    "GrowthMetrics",
    "growth_rate",
    "cagr",
    "average_growth",
    "project_value",
]
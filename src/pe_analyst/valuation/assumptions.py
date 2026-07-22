from dataclasses import dataclass


@dataclass(slots=True)
class ValuationAssumptions:
    projection_years: int = 5
    revenue_growth: float = 0.08
    ebit_margin: float = 0.22
    tax_rate: float = 0.25
    depreciation_pct: float = 0.03
    capex_pct: float = 0.04
    nwc_pct: float = 0.02
    wacc: float = 0.10
    terminal_growth: float = 0.025

from dataclasses import dataclass


@dataclass(slots=True)
class ValuationAssumptions:
    projection_years: int = 5
    revenue_growth: float = 0.08
    ebit_margin: float = 0.22
    depreciation_pct: float = 0.03
    capex_pct: float = 0.04
    nwc_pct: float = 0.02
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.025
    cash: float = 0.0
    debt: float = 0.0
    shares_outstanding: float = 1.0

from dataclasses import dataclass


@dataclass(slots=True)
class ProjectionResult:
    year: int
    revenue: float
    ebitda: float
    depreciation: float
    ebit: float
    nopat: float
    capex: float
    delta_nwc: float
    fcff: float

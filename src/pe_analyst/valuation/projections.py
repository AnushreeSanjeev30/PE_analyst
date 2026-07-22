from dataclasses import dataclass


@dataclass(slots=True)
class ProjectionResult:
    year: int
    revenue: float
    ebit: float
    nopat: float
    depreciation: float
    capex: float
    change_nwc: float
    fcff: float

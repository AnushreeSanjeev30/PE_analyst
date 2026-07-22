from __future__ import annotations

from .assumptions import ValuationAssumptions
from .projections import ProjectionResult


class DCFEngine:
    def __init__(self, assumptions: ValuationAssumptions):
        self.assumptions = assumptions

    def project(self, revenue: float) -> list[ProjectionResult]:
        projections = []
        current = revenue

        for year in range(1, self.assumptions.projection_years + 1):
            current *= 1 + self.assumptions.revenue_growth
            ebit = current * self.assumptions.ebit_margin
            nopat = ebit * (1 - self.assumptions.tax_rate)
            depreciation = current * self.assumptions.depreciation_pct
            capex = current * self.assumptions.capex_pct
            nwc = current * self.assumptions.nwc_pct
            fcff = nopat + depreciation - capex - nwc

            projections.append(
                ProjectionResult(
                    year=year,
                    revenue=current,
                    ebit=ebit,
                    nopat=nopat,
                    depreciation=depreciation,
                    capex=capex,
                    change_nwc=nwc,
                    fcff=fcff,
                )
            )

        return projections

    def enterprise_value(self, revenue: float) -> float:
        projections = self.project(revenue)
        wacc = self.assumptions.wacc

        pv = 0.0
        for p in projections:
            pv += p.fcff / ((1 + wacc) ** p.year)

        terminal_fcff = projections[-1].fcff * (1 + self.assumptions.terminal_growth)
        terminal = terminal_fcff / (wacc - self.assumptions.terminal_growth)
        terminal_pv = terminal / ((1 + wacc) ** projections[-1].year)

        return pv + terminal_pv

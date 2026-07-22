from __future__ import annotations

from .assumptions import ValuationAssumptions
from .discount import DiscountEngine
from .exceptions import InvalidAssumptionError
from .projections import ProjectionResult
from .results import DCFResult
from .terminal import TerminalValueEngine


class DCFEngine:
    def __init__(self, assumptions: ValuationAssumptions):
        self.assumptions = assumptions
        self._validate_assumptions()

    def _validate_assumptions(self) -> None:
        if self.assumptions.projection_years <= 0:
            raise InvalidAssumptionError("projection_years must be greater than 0.")

        if self.assumptions.wacc <= 0:
            raise InvalidAssumptionError("wacc must be greater than 0.")

        if self.assumptions.terminal_growth >= self.assumptions.wacc:
            raise InvalidAssumptionError("terminal_growth must be less than wacc.")

        if self.assumptions.shares_outstanding <= 0:
            raise InvalidAssumptionError("shares_outstanding must be greater than 0.")

    def project(self, revenue: float) -> list[ProjectionResult]:
        if revenue <= 0:
            raise InvalidAssumptionError("revenue must be greater than 0.")

        projections: list[ProjectionResult] = []
        current_revenue = revenue
        previous_nwc = revenue * self.assumptions.nwc_pct

        for year in range(1, self.assumptions.projection_years + 1):
            current_revenue *= 1 + self.assumptions.revenue_growth

            depreciation = current_revenue * self.assumptions.depreciation_pct
            ebit = current_revenue * self.assumptions.ebit_margin
            ebitda = ebit + depreciation
            nopat = ebit * (1 - self.assumptions.tax_rate)
            capex = current_revenue * self.assumptions.capex_pct

            nwc = current_revenue * self.assumptions.nwc_pct
            delta_nwc = nwc - previous_nwc
            previous_nwc = nwc

            fcff = nopat + depreciation - capex - delta_nwc

            projections.append(
                ProjectionResult(
                    year=year,
                    revenue=current_revenue,
                    ebitda=ebitda,
                    depreciation=depreciation,
                    ebit=ebit,
                    nopat=nopat,
                    capex=capex,
                    delta_nwc=delta_nwc,
                    fcff=fcff,
                )
            )

        return projections

    def calculate(self, revenue: float) -> DCFResult:
        projections = self.project(revenue)

        pv_fcff = 0.0
        for p in projections:
            pv_fcff += DiscountEngine.present_value(
                cash_flow=p.fcff,
                rate=self.assumptions.wacc,
                year=p.year,
            )

        terminal_value = TerminalValueEngine.gordon_growth(
            fcff=projections[-1].fcff,
            wacc=self.assumptions.wacc,
            growth=self.assumptions.terminal_growth,
        )
        terminal_pv = DiscountEngine.present_value(
            cash_flow=terminal_value,
            rate=self.assumptions.wacc,
            year=projections[-1].year,
        )

        enterprise_value = pv_fcff + terminal_pv
        equity_value = enterprise_value + self.assumptions.cash - self.assumptions.debt
        price_per_share = equity_value / self.assumptions.shares_outstanding

        return DCFResult(
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            terminal_value=terminal_pv,
            pv_fcff=pv_fcff,
            price_per_share=price_per_share,
        )

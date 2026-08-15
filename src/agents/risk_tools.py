"""Deterministic private-equity risk scoring and metric extraction."""

from __future__ import annotations

from typing import Any

from .risk_models import RiskFactor, RiskLevel


class RiskTools:
    """Evaluates explicit scorecard rules; it does not infer missing financial data."""

    @staticmethod
    def level(score: float) -> RiskLevel:
        if score < 25:
            return RiskLevel.LOW
        if score < 50:
            return RiskLevel.MODERATE
        if score < 75:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    @staticmethod
    def _score(value: float, bands: tuple[float, float, float], inverse: bool) -> float:
        low, medium, high = bands
        if inverse:
            return (
                10.0
                if value >= low
                else 35.0
                if value >= medium
                else 70.0
                if value >= high
                else 95.0
            )
        return (
            10.0 if value <= low else 35.0 if value <= medium else 70.0 if value <= high else 95.0
        )

    def evaluate(self, state: Any) -> tuple[list[RiskFactor], list[str]]:
        ratios = state.ratios
        current = state.financial_data.get("current")
        risk_inputs = state.metadata.get("risk_inputs", {})
        factors: list[RiskFactor] = []
        missing: list[str] = []

        current_ratio = ratios.get("current_ratio")
        if current_ratio is None:
            missing.append("current_ratio")
        else:
            score = self._score(float(current_ratio), (1.5, 1.0, 0.8), inverse=True)
            factors.append(
                RiskFactor(
                    "Liquidity",
                    score,
                    self.level(score),
                    "Current ratio compared with liquidity thresholds.",
                    float(current_ratio),
                    1.5,
                )
            )

        leverage = ratios.get("debt_to_ebitda")
        if leverage is None:
            missing.append("debt_to_ebitda")
        else:
            score = self._score(float(leverage), (2.5, 4.0, 5.0), inverse=False)
            factors.append(
                RiskFactor(
                    "Leverage",
                    score,
                    self.level(score),
                    "Net debt burden measured against EBITDA.",
                    float(leverage),
                    4.0,
                )
            )

        if current is None or current.interest_expense <= 0:
            missing.append("interest_coverage")
        else:
            coverage = current.ebit / current.interest_expense
            score = self._score(coverage, (4.0, 2.0, 1.0), inverse=True)
            factors.append(
                RiskFactor(
                    "Interest Coverage",
                    score,
                    self.level(score),
                    "EBIT divided by interest expense.",
                    coverage,
                    2.0,
                )
            )

        if current is None or current.capital_expenditure < 0:
            missing.append("cash_flow_coverage")
        else:
            cash_conversion = current.operating_cash_flow / max(current.ebitda, 1.0)
            score = self._score(cash_conversion, (0.75, 0.50, 0.25), inverse=True)
            factors.append(
                RiskFactor(
                    "Cash Flow",
                    score,
                    self.level(score),
                    "Operating cash flow divided by EBITDA.",
                    cash_conversion,
                    0.75,
                )
            )

        for metric_name, label, bands in (
            ("altman_z", "Altman Z", (3.0, 1.8, 1.0)),
            ("piotroski_score", "Piotroski F", (7.0, 5.0, 3.0)),
        ):
            value = risk_inputs.get(metric_name)
            if value is None:
                missing.append(metric_name)
                continue
            score = self._score(float(value), bands, inverse=True)
            factors.append(
                RiskFactor(
                    label,
                    score,
                    self.level(score),
                    f"User-supplied {label} score.",
                    float(value),
                    bands[1],
                )
            )

        valuation_report = state.metadata.get("valuation_report")
        if valuation_report is None:
            missing.append("valuation_report")
        else:
            lbo_irr = valuation_report.lbo_returns.irr if valuation_report.lbo_returns else 0.0
            score = self._score(lbo_irr, (0.20, 0.15, 0.10), inverse=True)
            factors.append(
                RiskFactor(
                    "Valuation",
                    score,
                    self.level(score),
                    "LBO IRR measured against the return hurdle.",
                    lbo_irr,
                    0.20,
                )
            )

        industry_score = risk_inputs.get("industry_risk_score")
        if industry_score is None:
            missing.append("industry_risk_score")
        else:
            score = min(max(float(industry_score), 0.0), 100.0)
            factors.append(
                RiskFactor(
                    "Industry",
                    score,
                    self.level(score),
                    "User-approved industry risk score.",
                    score,
                    50.0,
                )
            )
        return factors, missing

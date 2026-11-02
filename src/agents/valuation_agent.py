"""Private-equity valuation agent using DCF, comparable, and LBO engines."""

from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .state import AgentState
from .types import AgentResponse
from .valuation_models import (
    LBOReturnProfile,
    ScenarioAnalysis,
    ScenarioOutcome,
    ValuationFinding,
    ValuationMethod,
    ValuationRecommendation,
    ValuationReport,
    ValuationSummary,
)
from .valuation_tools import ValuationTools


class ValuationAgent(BaseAgent):
    """Produces an audit-ready valuation opinion from deterministic analyses."""

    def __init__(self) -> None:
        super().__init__("Valuation Agent")
        self.tools = ValuationTools()

    def validate(self, state: AgentState) -> None:
        super().validate(state)
        inputs = state.metadata.get("valuation_inputs")
        if not isinstance(inputs, dict):
            raise ValueError("state.metadata['valuation_inputs'] must contain valuation input data")
        missing = {"dcf", "comparables", "lbo"} - inputs.keys()
        if missing:
            raise ValueError(f"valuation_inputs is missing: {', '.join(sorted(missing))}")

    def execute(self, state: AgentState) -> AgentResponse:
        inputs = state.metadata["valuation_inputs"]
        dcf = self.tools.run_dcf(inputs["dcf"])
        comparables = self.tools.run_comparables(inputs["comparables"])
        lbo = self.tools.run_lbo(inputs["lbo"])
        scenarios = self.tools.run_scenarios(inputs["lbo"])
        report = self.generate_report(
            state.company_name,
            dcf,
            comparables,
            lbo,
            scenarios,
            inputs.get("current_price_per_share"),
        )
        state.valuation = {
            "dcf": dcf,
            "comparables": comparables,
            "lbo": lbo,
            "scenarios": scenarios,
            "report": report,
        }
        state.metadata["valuation_report"] = report
        return AgentResponse(
            agent_name=self.name,
            summary=report.summary.executive_summary,
            confidence=report.summary.confidence,
            findings=[finding.title for finding in report.findings],
            metadata={"report": report},
        )

    def generate_report(
        self,
        company: str,
        dcf: dict[str, Any],
        comparables: dict[str, Any],
        lbo: dict[str, Any],
        scenarios: dict[str, Any],
        current_price: Any,
    ) -> ValuationReport:
        dcf_result = dcf["result"]
        comp_price = float(comparables["implied_value_per_share"])
        dcf_price = float(dcf_result["price_per_share"])
        fair_value = (dcf_price * 0.60) + (comp_price * 0.40)
        price = float(current_price) if current_price is not None else None
        upside = ((fair_value / price) - 1.0) if price and price > 0 else None
        lbo_result = lbo["result"]
        irr = float(lbo_result["irr"])
        if irr >= 0.20 and (upside is None or upside >= 0.15):
            recommendation = ValuationRecommendation.ACCEPT
        elif irr >= 0.15 and (upside is None or upside >= 0.0):
            recommendation = ValuationRecommendation.WATCH
        else:
            recommendation = ValuationRecommendation.REJECT
        confidence = min(0.95, 0.55 + (0.10 if comparables["peer_count"] >= 5 else 0.05) + 0.15)
        summary = ValuationSummary(
            company_name=company,
            intrinsic_value_per_share=dcf_price,
            fair_value_per_share=fair_value,
            current_price_per_share=price,
            upside_downside_pct=upside,
            margin_of_safety_pct=upside,
            confidence=confidence,
            recommendation=recommendation,
            executive_summary=(
                f"{company} has a blended fair value of {fair_value:.2f} per share and an "
                f"LBO IRR of {irr:.1%}; valuation recommendation: {recommendation.value}."
            ),
        )
        methods = [
            ValuationMethod(
                "DCF",
                dcf_result["enterprise_value"],
                dcf_result["equity_value"],
                dcf_price,
                0.60,
                0.85,
                dcf["assumptions"],
            ),
            ValuationMethod(
                "Comparable Companies",
                comparables["implied_enterprise_value"],
                comparables["implied_equity_value"],
                comp_price,
                0.40,
                0.70,
                {
                    "peer_count": comparables["peer_count"],
                    "median_ev_revenue": comparables["median_ev_revenue"],
                    "median_ev_ebitda": comparables["median_ev_ebitda"],
                },
            ),
        ]
        lbo_profile = LBOReturnProfile(
            lbo["assumptions"]["purchase_price"],
            lbo_result["exit_enterprise_value"],
            lbo_result["exit_equity"],
            irr,
            lbo_result["moic"],
            lbo_result["debt_remaining"],
            lbo["assumptions"]["holding_period"],
        )
        scenario_analysis = ScenarioAnalysis(
            target_irr=scenarios["target_irr"],
            outcomes=[
                ScenarioOutcome(
                    outcome.name,
                    outcome.exit_multiple,
                    outcome.result.irr,
                    outcome.result.moic,
                    outcome.result.exit_equity,
                )
                for outcome in scenarios["outcomes"]
            ],
            breakeven_exit_multiple=scenarios["breakeven_exit_multiple"],
        )
        bear_case = next(
            (o for o in scenario_analysis.outcomes if o.name == "Bear"),
            scenario_analysis.outcomes[0],
        )
        findings = [
            ValuationFinding(
                "DCF intrinsic value calculated", f"DCF indicates {dcf_price:.2f} per share."
            ),
            ValuationFinding(
                "Comparable-company fair value calculated",
                f"{comparables['peer_count']} peers imply {comp_price:.2f} per share.",
            ),
            ValuationFinding(
                "LBO return threshold assessed",
                f"Base-case IRR is {irr:.1%} and MOIC is {float(lbo_result['moic']):.2f}x.",
                "WARNING" if irr < 0.20 else "INFO",
            ),
            ValuationFinding(
                "Downside scenario assessed",
                f"Bear case IRR is {bear_case.irr:.1%} at a {bear_case.exit_multiple:.1f}x exit.",
                "WARNING" if bear_case.irr < 0.0 else "INFO",
            ),
        ]
        return ValuationReport(
            summary,
            methods,
            lbo_profile,
            scenario_analysis,
            findings,
            {"dcf_weight": 0.60, "comparables_weight": 0.40, "target_irr": 0.20},
        )

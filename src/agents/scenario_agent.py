"""Scenario Analysis Agent: how robust are the returns if the plan doesn't go to plan?

Reuses the deal's LBO inputs (``valuation_inputs["lbo"]``) and optional overrides in
``state.metadata["scenario_inputs"]``::

    {
        "target_irr": 0.20,
        "scenarios": [{"name": "Bear", "probability": 0.3, "ebitda_multiplier": 0.8,
                       "revenue_multiplier": 0.9, "exit_multiple_delta": -1.5}, ...],
        "exit_multiples": [6, 7, 8, 9, 10],
        "ebitda_multipliers": [0.8, 0.9, 1.0, 1.1, 1.2],
    }
"""

from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .narration import to_jsonable
from .scenario_models import ReturnResilience, ScenarioReport, ScenarioSummary
from .scenario_tools import DEFAULT_TARGET_IRR, ScenarioTools
from .state import AgentState
from .types import AgentResponse


class ScenarioAnalysisAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("Scenario Analysis Agent")
        self.tools = ScenarioTools()

    def validate(self, state: AgentState) -> None:
        super().validate(state)
        lbo = state.metadata.get("valuation_inputs", {}).get("lbo")
        if not isinstance(lbo, dict):
            raise ValueError("Scenario Analysis Agent requires valuation_inputs['lbo']")

    def execute(self, state: AgentState) -> AgentResponse:
        overrides: dict[str, Any] = state.metadata.get("scenario_inputs") or {}
        target_irr = float(overrides.get("target_irr", DEFAULT_TARGET_IRR))
        assumptions, projection = self.tools.parse_lbo(state.metadata["valuation_inputs"]["lbo"])
        cases = self.tools.run_cases(
            assumptions, projection, self.tools.parse_cases(overrides.get("scenarios")), target_irr
        )

        weighted_irr = sum(case.irr * case.probability for case in cases)
        weighted_moic = sum(case.moic * case.probability for case in cases)
        hit_probability = sum(case.probability for case in cases if case.meets_target)
        resilience = self.tools.resilience(cases, weighted_irr, target_irr)
        worst = min(cases, key=lambda case: case.irr)

        breakeven = self.tools.breakeven(assumptions, projection, target_irr)
        preservation = self.tools.capital_preservation_multiple(assumptions, projection)
        grid = self.tools.sensitivity(
            assumptions,
            projection,
            overrides.get("exit_multiples"),
            overrides.get("ebitda_multipliers"),
        )

        findings = [
            f"Probability-weighted IRR {weighted_irr:.1%} vs {target_irr:.1%} target.",
            f"Worst case ({worst.name}) returns {worst.irr:.1%} IRR / {worst.moic:.2f}x MOIC.",
            f"{hit_probability:.0%} of scenario probability clears the target IRR.",
        ]
        if breakeven is not None:
            findings.append(
                f"Exit multiple of {breakeven:.2f}x needed for the target IRR "
                f"(underwritten at {assumptions.exit_multiple:.2f}x)."
            )
        if preservation is not None:
            findings.append(f"Equity is returned in full at an exit of {preservation:.2f}x.")
        if worst.moic < 1.0:
            findings.append(f"{worst.name} case loses equity capital.")

        summary = ScenarioSummary(
            company_name=state.company_name,
            resilience=resilience,
            target_irr=target_irr,
            probability_weighted_irr=weighted_irr,
            probability_weighted_moic=weighted_moic,
            confidence=0.80 if resilience != ReturnResilience.FRAGILE else 0.70,
            executive_summary=(
                f"Returns are {resilience.value.lower()} across {len(cases)} scenarios: "
                f"probability-weighted IRR {weighted_irr:.1%}, worst case {worst.irr:.1%}."
            ),
        )
        report = ScenarioReport(
            summary=summary,
            cases=cases,
            breakeven_exit_multiple=breakeven,
            capital_preservation_exit_multiple=preservation,
            probability_of_meeting_target=hit_probability,
            downside_capital_loss=worst.moic < 1.0,
            sensitivity=grid,
            findings=findings,
        )
        state.metadata["scenario_report"] = report
        return AgentResponse(
            self.name, summary.executive_summary, summary.confidence, findings, {"report": report}
        )

    def narrative_facts(self, state: AgentState, response: AgentResponse) -> dict[str, Any]:
        facts = super().narrative_facts(state, response)
        report: ScenarioReport = response.metadata["report"]
        # The full grid is 25 cells of noise for a narrator; keep the corners and centre.
        if report.sensitivity is not None:
            cells = report.sensitivity.cells
            facts["output"] = {
                "report": {**_without_grid(report), "sensitivity_extremes": [
                    cells[0], cells[len(cells) // 2], cells[-1]
                ]}
            }
        return facts


def _without_grid(report: ScenarioReport) -> dict[str, Any]:
    data = to_jsonable(report)
    data.pop("sensitivity", None)
    return dict(data)


__all__ = ["ScenarioAnalysisAgent"]

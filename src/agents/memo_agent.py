"""Investment Memo Agent: assembles the committee memo from every specialist report.

The memo body is built deterministically from the reports, so it is always produced and every
figure in it is traceable. When a narrator is configured the agent also asks the LLM for a
written draft over the same facts (``InvestmentMemo.llm_draft``); that draft is advisory and is
flagged if it cites figures the reports don't contain.
"""

from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .memo_models import InvestmentMemo, MemoSection
from .narration import Narrative
from .prompts import MEMO_INSTRUCTIONS
from .state import AgentState
from .types import AgentResponse


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _money(value: float | None) -> str:
    return "n/a" if value is None else f"{value:,.2f}"


class InvestmentMemoAgent(BaseAgent):

    narration_max_tokens = 2_500

    def __init__(self) -> None:
        super().__init__("Investment Memo Agent")

    @property
    def narration_instructions(self) -> str | None:
        return MEMO_INSTRUCTIONS

    def validate(self, state: AgentState) -> None:
        super().validate(state)
        if state.metadata.get("ic_decision") is None:
            raise ValueError("Investment Memo Agent requires the IC decision")

    def execute(self, state: AgentState) -> AgentResponse:
        meta = state.metadata
        decision = meta["ic_decision"]
        sections = [
            self._executive_summary(decision, meta),
            self._company_and_industry(meta.get("industry_report")),
            self._financials(meta.get("financial_report")),
            self._valuation(meta.get("valuation_report")),
            self._scenarios(meta.get("scenario_report")),
            self._risks(meta.get("risk_report"), meta.get("due_diligence_report")),
            self._decision(decision),
            self._next_steps(decision),
        ]
        memo = InvestmentMemo(state.company_name, decision.final_recommendation, sections)
        memo.markdown = memo.render_markdown()
        meta["investment_memo"] = memo
        return AgentResponse(
            self.name,
            f"Investment memo prepared for {state.company_name}: "
            f"{decision.final_recommendation}.",
            0.90,
            [section.heading for section in sections],
            {"memo": memo},
        )

    def narrative_facts(self, state: AgentState, response: AgentResponse) -> dict[str, Any]:
        memo: InvestmentMemo = response.metadata["memo"]
        return {
            "company": state.company_name,
            "recommendation": memo.recommendation,
            "sections": [
                {"heading": s.heading, "body": s.body, "bullets": s.bullets}
                for s in memo.sections
            ],
        }

    def on_narrative(
        self, state: AgentState, response: AgentResponse, narrative: Narrative
    ) -> None:
        memo: InvestmentMemo = response.metadata["memo"]
        memo.llm_draft = narrative.commentary or None
        memo.llm_warnings = list(narrative.warnings)

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    @staticmethod
    def _executive_summary(decision: Any, meta: dict[str, Any]) -> MemoSection:
        committee = decision.committee_vote.summary
        bullets = list(decision.committee_vote.investment_thesis[:3])
        scenario = meta.get("scenario_report")
        if scenario is not None:
            bullets.append(scenario.summary.executive_summary)
        return MemoSection(
            "Executive Summary",
            f"The committee recommends {decision.final_recommendation} on "
            f"{decision.company_name}. Expected IRR {_pct(committee.expected_irr)}; "
            f"target price {_money(committee.target_price)} per share; committee confidence "
            f"{committee.confidence:.0%}.",
            bullets,
        )

    @staticmethod
    def _company_and_industry(industry: Any) -> MemoSection:
        if industry is None:
            return MemoSection("Company and Industry", "Industry analysis unavailable.")
        bullets = [
            f"{finding.title}: {finding.analysis}"
            + (
                f" (p. {finding.citations[0].page_number}, {finding.citations[0].source})"
                if finding.citations
                else ""
            )
            for finding in industry.findings[:4]
        ]
        return MemoSection("Company and Industry", industry.summary.executive_summary, bullets)

    @staticmethod
    def _financials(financial: Any) -> MemoSection:
        if financial is None:
            return MemoSection("Financial Performance", "Financial analysis unavailable.")
        bullets = [
            f"{metric.name}: {metric.value:,.2f}{metric.unit}"
            + (f" (benchmark {metric.benchmark}{metric.unit})" if metric.benchmark else "")
            for metric in financial.metrics
        ]
        bullets += [f"Strength: {item.title}" for item in financial.strengths]
        bullets += [f"Weakness: {item.title}" for item in financial.weaknesses]
        return MemoSection("Financial Performance", financial.summary.executive_summary, bullets)

    @staticmethod
    def _valuation(valuation: Any) -> MemoSection:
        if valuation is None:
            return MemoSection("Valuation", "Valuation unavailable.")
        bullets = [
            f"{method.name}: equity value {_money(method.equity_value)}, "
            f"per share {_money(method.value_per_share)}, weight {method.weight:.0%}"
            for method in valuation.methods
        ]
        if valuation.lbo_returns is not None:
            lbo = valuation.lbo_returns
            bullets.append(
                f"LBO: {lbo.irr:.1%} IRR, {lbo.moic:.2f}x MOIC over "
                f"{lbo.holding_period_years} years"
            )
        return MemoSection("Valuation", valuation.summary.executive_summary, bullets)

    @staticmethod
    def _scenarios(scenario: Any) -> MemoSection:
        if scenario is None:
            return MemoSection("Returns and Scenarios", "Scenario analysis unavailable.")
        bullets = [
            f"{case.name} ({case.probability:.0%}): {case.irr:.1%} IRR, {case.moic:.2f}x MOIC "
            f"at {case.exit_multiple:.1f}x exit"
            for case in scenario.cases
        ]
        bullets += scenario.findings[3:]
        return MemoSection("Returns and Scenarios", scenario.summary.executive_summary, bullets)

    @staticmethod
    def _risks(risk: Any, diligence: Any) -> MemoSection:
        bullets: list[str] = []
        body = []
        if risk is not None:
            body.append(risk.summary.executive_summary)
            bullets += [
                f"{item.title} ({item.severity.value}): {item.mitigation}"
                for item in risk.major_risks[:5]
            ]
            bullets += [f"Missing data: {item}" for item in risk.missing_data]
        if diligence is not None:
            body.append(diligence.summary.executive_summary)
            bullets += [
                f"Red flag - {flag.title} ({flag.severity.value}, p. "
                f"{flag.citation.page_number})"
                for flag in diligence.red_flags[:5]
            ]
        return MemoSection(
            "Key Risks and Diligence", " ".join(body) or "Risk analysis unavailable.", bullets
        )

    @staticmethod
    def _decision(decision: Any) -> MemoSection:
        bullets = [
            f"Deal Partner: {decision.deal_partner.position.value}",
            f"Risk Officer: {decision.risk_officer.verdict.value}",
            f"Operating Partner: {decision.operating_partner.potential.value} value creation",
        ]
        bullets += [f"Dissent - {item.member}: {item.rationale}" for item in decision.dissent]
        return MemoSection(
            "Committee Decision",
            f"{'Unanimous' if decision.unanimous else 'Split'} decision: "
            f"{decision.final_recommendation}. {decision.chair_rationale}",
            bullets,
        )

    @staticmethod
    def _next_steps(decision: Any) -> MemoSection:
        steps = list(decision.committee_vote.conditions_precedent)
        steps += decision.risk_officer.required_conditions
        steps += [f"Value lever: {lever}" for lever in decision.operating_partner.value_levers]
        unique = list(dict.fromkeys(steps))
        return MemoSection(
            "Next Steps",
            "Conditions and workstreams before signing:"
            if unique
            else "No conditions precedent were raised.",
            unique,
        )


__all__ = ["InvestmentMemoAgent"]

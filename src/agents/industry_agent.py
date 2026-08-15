"""Document-grounded industry and competitive analysis agent."""

from __future__ import annotations

from .base_agent import BaseAgent
from .industry_models import CompetitivePosition, IndustryFinding, IndustryReport, IndustrySummary
from .industry_tools import IndustryTools
from .state import AgentState
from .types import AgentResponse


class IndustryAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("Industry Agent")
        self.tools = IndustryTools()

    def execute(self, state: AgentState) -> AgentResponse:
        raw = self.tools.validate_and_normalize(state.metadata.get("industry_inputs"))
        evidence = raw["evidence"]
        competitors = self.tools.competitors(raw.get("competitors", []))
        growth = raw.get("market_growth_pct")
        position = CompetitivePosition(raw.get("competitive_position", "Neutral"))
        confidence = sum(float(item["confidence"]) for item in evidence) / len(evidence)
        findings = [
            IndustryFinding(
                "Market outlook",
                self._claims(evidence, "market"),
                self.tools.citations(evidence, "market"),
            ),
            IndustryFinding(
                "Competitive dynamics",
                self._claims(evidence, "competition"),
                self.tools.citations(evidence, "competition"),
            ),
            IndustryFinding(
                "Management commentary",
                self._claims(evidence, "management"),
                self.tools.citations(evidence, "management"),
            ),
        ]
        report = IndustryReport(
            IndustrySummary(
                raw["industry_name"],
                growth,
                position,
                confidence,
                (
                    f"{state.company_name} operates in {raw['industry_name']} with a "
                    f"{position.value.lower()} competitive position."
                ),
            ),
            competitors,
            findings,
            raw.get("porter_forces", {}),
            raw.get("management_themes", []),
            len(evidence),
        )
        state.industry = {"report": report, "industry_name": raw["industry_name"]}
        state.metadata["industry_report"] = report
        return AgentResponse(
            self.name,
            report.summary.executive_summary,
            confidence,
            [finding.title for finding in findings],
            {"report": report},
        )

    @staticmethod
    def _claims(evidence: list[dict[str, object]], topic: str) -> str:
        claims = [str(item["claim"]) for item in evidence if item["topic"] == topic]
        return " ".join(claims) if claims else "No evidence was supplied for this topic."

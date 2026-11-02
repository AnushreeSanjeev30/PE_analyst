"""Document-grounded red-flag detection agent for private-equity due diligence."""

from __future__ import annotations

from .base_agent import BaseAgent
from .due_diligence_models import (
    DueDiligenceAssessment,
    DueDiligenceReport,
    DueDiligenceSummary,
    RedFlag,
    RedFlagSeverity,
)
from .due_diligence_tools import DueDiligenceTools
from .state import AgentState
from .types import AgentResponse


class DueDiligenceAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("Due Diligence Agent")
        self.tools = DueDiligenceTools()

    def execute(self, state: AgentState) -> AgentResponse:
        items = self.tools.validate_and_normalize(state.metadata.get("due_diligence_inputs"))
        red_flags = self.tools.evaluate(items)
        severities = {flag.severity for flag in red_flags}
        if RedFlagSeverity.CRITICAL in severities:
            assessment = DueDiligenceAssessment.CRITICAL
        elif severities:
            assessment = DueDiligenceAssessment.CAUTION
        else:
            assessment = DueDiligenceAssessment.CLEAR

        confidence = (
            sum(flag.citation.confidence for flag in red_flags) / len(red_flags)
            if red_flags
            else (0.85 if items else 0.40)
        )

        report = DueDiligenceReport(
            summary=DueDiligenceSummary(
                company_name=state.company_name,
                assessment=assessment,
                red_flag_count=len(red_flags),
                confidence=confidence,
                executive_summary=self._summary_text(
                    state.company_name, assessment, red_flags, items
                ),
            ),
            red_flags=red_flags,
            items_reviewed=len(items),
        )
        state.due_diligence = {"report": report, "assessment": assessment.value}
        state.metadata["due_diligence_report"] = report
        return AgentResponse(
            self.name,
            report.summary.executive_summary,
            confidence,
            [flag.title for flag in red_flags],
            {"report": report},
        )

    @staticmethod
    def _summary_text(
        company: str,
        assessment: DueDiligenceAssessment,
        red_flags: list[RedFlag],
        items: list[dict[str, object]],
    ) -> str:
        if not items:
            return (
                f"{company} has no source-grounded diligence items to review; "
                "due diligence is incomplete."
            )
        if not red_flags:
            return f"{company} shows no red flags across {len(items)} reviewed diligence item(s)."
        return (
            f"{company} diligence review found {len(red_flags)} red flag(s) across "
            f"{len(items)} reviewed item(s); overall assessment: {assessment.value}."
        )

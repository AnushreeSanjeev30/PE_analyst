from types import SimpleNamespace

import pytest

from agents import AgentState, InvestmentCommitteeAgent
from agents.due_diligence_models import DueDiligenceAssessment
from agents.financial_models import FinancialHealth
from agents.industry_models import CompetitivePosition
from agents.risk_models import RiskLevel


def _state(dd_assessment: DueDiligenceAssessment = DueDiligenceAssessment.CLEAR) -> AgentState:
    financial = SimpleNamespace(summary=SimpleNamespace(health=FinancialHealth.GOOD))
    valuation = SimpleNamespace(
        summary=SimpleNamespace(fair_value_per_share=125.0, upside_downside_pct=0.20),
        lbo_returns=SimpleNamespace(irr=0.24),
    )
    risk = SimpleNamespace(
        summary=SimpleNamespace(level=RiskLevel.MODERATE, score=35.0),
        major_risks=[SimpleNamespace(title="Customer concentration")],
        mitigations=["Validate customer retention."],
    )
    industry = SimpleNamespace(
        summary=SimpleNamespace(competitive_position=CompetitivePosition.STRONG),
    )
    due_diligence = SimpleNamespace(
        summary=SimpleNamespace(assessment=dd_assessment, red_flag_count=0),
        red_flags=[],
    )
    return AgentState(
        company_name="ExampleCo",
        metadata={
            "financial_report": financial,
            "valuation_report": valuation,
            "risk_report": risk,
            "industry_report": industry,
            "due_diligence_report": due_diligence,
        },
    )


def test_investment_committee_produces_a_buy_recommendation() -> None:
    state = _state()

    report = InvestmentCommitteeAgent().run(state).metadata["report"]

    assert report.summary.recommendation == "BUY"
    assert report.summary.target_price == 125.0
    assert report.summary.expected_irr == 0.24
    assert len(report.votes) == 5
    assert state.metadata["investment_committee_report"] is report


def test_investment_committee_rejects_on_critical_due_diligence_finding() -> None:
    state = _state(dd_assessment=DueDiligenceAssessment.CRITICAL)

    report = InvestmentCommitteeAgent().run(state).metadata["report"]

    assert report.summary.recommendation == "REJECT"


def test_investment_committee_requires_all_specialist_reports() -> None:
    with pytest.raises(ValueError, match="requires financial"):
        InvestmentCommitteeAgent().run(AgentState(company_name="ExampleCo"))

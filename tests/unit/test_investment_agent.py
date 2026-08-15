from types import SimpleNamespace

import pytest

from agents import AgentState, InvestmentCommitteeAgent
from agents.financial_models import FinancialHealth
from agents.industry_models import CompetitivePosition
from agents.risk_models import RiskLevel


def _state() -> AgentState:
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
    return AgentState(
        company_name="ExampleCo",
        metadata={
            "financial_report": financial,
            "valuation_report": valuation,
            "risk_report": risk,
            "industry_report": industry,
        },
    )


def test_investment_committee_produces_a_buy_recommendation() -> None:
    state = _state()

    report = InvestmentCommitteeAgent().run(state).metadata["report"]

    assert report.summary.recommendation == "BUY"
    assert report.summary.target_price == 125.0
    assert report.summary.expected_irr == 0.24
    assert len(report.votes) == 4
    assert state.metadata["investment_committee_report"] is report


def test_investment_committee_requires_all_specialist_reports() -> None:
    with pytest.raises(ValueError, match="requires financial"):
        InvestmentCommitteeAgent().run(AgentState(company_name="ExampleCo"))

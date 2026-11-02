from types import SimpleNamespace

import pytest

from agents import (
    AgentState,
    DealPartnerAgent,
    ICChairpersonAgent,
    InvestmentCommitteeAgent,
    OperatingPartnerAgent,
    RiskOfficerAgent,
)
from agents.due_diligence_models import DueDiligenceAssessment
from agents.financial_models import FinancialHealth
from agents.ic_simulation_models import PartnerPosition, RiskOfficerVerdict, ValueCreationPotential
from agents.industry_models import CompetitivePosition
from agents.investment_models import CommitteeRecommendation
from agents.risk_models import RiskLevel


def _scenario(name: str, irr: float, exit_multiple: float = 8.0):
    return SimpleNamespace(name=name, irr=irr, exit_multiple=exit_multiple)


def _state(
    *,
    health: FinancialHealth = FinancialHealth.GOOD,
    irr: float = 0.24,
    upside: float | None = 0.20,
    position: CompetitivePosition = CompetitivePosition.STRONG,
    risk_level: RiskLevel = RiskLevel.MODERATE,
    dd_assessment: DueDiligenceAssessment = DueDiligenceAssessment.CLEAR,
    bear_irr: float = -0.05,
    base_irr: float = 0.18,
    bull_irr: float = 0.30,
    management_themes: list[str] | None = None,
) -> AgentState:
    financial = SimpleNamespace(summary=SimpleNamespace(health=health))
    scenario_analysis = SimpleNamespace(
        outcomes=[
            _scenario("Bear", bear_irr, 7.0),
            _scenario("Base", base_irr, 8.0),
            _scenario("Bull", bull_irr, 9.0),
        ]
    )
    valuation = SimpleNamespace(
        summary=SimpleNamespace(upside_downside_pct=upside, fair_value_per_share=125.0),
        lbo_returns=SimpleNamespace(irr=irr),
        scenario_analysis=scenario_analysis,
    )
    risk = SimpleNamespace(
        summary=SimpleNamespace(level=risk_level, score=35.0),
        major_risks=[SimpleNamespace(title="Customer concentration")],
        mitigations=["Validate customer retention."],
    )
    industry = SimpleNamespace(
        summary=SimpleNamespace(competitive_position=position),
        management_themes=management_themes or ["Cross-sell expansion"],
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


def _run_committee_and_personas(state: AgentState) -> None:
    InvestmentCommitteeAgent().run(state)
    DealPartnerAgent().run(state)
    RiskOfficerAgent().run(state)
    OperatingPartnerAgent().run(state)


def test_deal_partner_advocates_on_strong_fundamentals() -> None:
    state = _state()

    opinion = DealPartnerAgent().run(state).metadata["opinion"]

    assert opinion.position == PartnerPosition.ADVOCATE
    assert state.metadata["deal_partner_opinion"] is opinion


def test_deal_partner_opposes_on_weak_health() -> None:
    state = _state(health=FinancialHealth.WEAK, irr=0.05)

    opinion = DealPartnerAgent().run(state).metadata["opinion"]

    assert opinion.position == PartnerPosition.OPPOSE


def test_risk_officer_vetoes_on_critical_due_diligence() -> None:
    state = _state(dd_assessment=DueDiligenceAssessment.CRITICAL)

    opinion = RiskOfficerAgent().run(state).metadata["opinion"]

    assert opinion.verdict == RiskOfficerVerdict.VETO


def test_risk_officer_vetoes_on_a_near_total_wipeout_bear_case() -> None:
    state = _state(bear_irr=-0.60)

    opinion = RiskOfficerAgent().run(state).metadata["opinion"]

    assert opinion.verdict == RiskOfficerVerdict.VETO


def test_risk_officer_clears_a_clean_deal() -> None:
    state = _state(risk_level=RiskLevel.LOW, bear_irr=0.05)

    opinion = RiskOfficerAgent().run(state).metadata["opinion"]

    assert opinion.verdict == RiskOfficerVerdict.CLEAR


def test_operating_partner_strong_potential_on_wide_bull_base_spread() -> None:
    state = _state(base_irr=0.15, bull_irr=0.30)

    opinion = OperatingPartnerAgent().run(state).metadata["opinion"]

    assert opinion.potential == ValueCreationPotential.STRONG


def test_operating_partner_limited_potential_on_narrow_spread() -> None:
    state = _state(base_irr=0.20, bull_irr=0.21)

    opinion = OperatingPartnerAgent().run(state).metadata["opinion"]

    assert opinion.potential == ValueCreationPotential.LIMITED


def test_chairperson_follows_committee_scorecard_when_everyone_agrees() -> None:
    state = _state(bear_irr=0.02)
    _run_committee_and_personas(state)

    decision = ICChairpersonAgent().run(state).metadata["decision"]

    committee_report = state.metadata["investment_committee_report"]
    assert decision.final_recommendation == committee_report.summary.recommendation.value
    assert decision.unanimous
    assert state.recommendation["recommendation"] == decision.final_recommendation


def test_chairperson_veto_overrides_a_buy_from_the_scorecard() -> None:
    state = _state(dd_assessment=DueDiligenceAssessment.CRITICAL)
    _run_committee_and_personas(state)
    committee_report = state.metadata["investment_committee_report"]
    assert committee_report.summary.recommendation == CommitteeRecommendation.REJECT

    decision = ICChairpersonAgent().run(state).metadata["decision"]

    assert decision.final_recommendation == "REJECT"
    assert decision.risk_officer.verdict == RiskOfficerVerdict.VETO


def test_chairperson_downgrades_buy_to_hold_on_conditional_risk_verdict() -> None:
    state = _state(risk_level=RiskLevel.HIGH, bear_irr=0.02)
    _run_committee_and_personas(state)
    committee_recommendation = state.metadata["investment_committee_report"].summary.recommendation

    decision = ICChairpersonAgent().run(state).metadata["decision"]

    if committee_recommendation == CommitteeRecommendation.BUY:
        assert decision.final_recommendation == "HOLD"
        assert not decision.unanimous


def test_chairperson_requires_committee_vote_and_all_partner_opinions() -> None:
    with pytest.raises(ValueError, match="requires the committee vote"):
        ICChairpersonAgent().run(AgentState(company_name="ExampleCo"))

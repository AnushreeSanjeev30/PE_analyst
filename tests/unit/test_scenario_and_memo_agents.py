from dataclasses import replace

import pytest
from tests.unit.test_deal_analysis import (
    _due_diligence_inputs,
    _financial_data,
    _industry_inputs,
    _valuation_inputs,
)

from agents import AgentState, DealAnalysisInputs, ScenarioAnalysisAgent, run_deal_analysis
from agents.financial_agent import FinancialAgent
from agents.financial_models import FinancialHealth
from agents.scenario_models import ReturnResilience


def _scenario_state(**scenario_inputs: object) -> AgentState:
    state = AgentState(company_name="ExampleCo")
    state.metadata["valuation_inputs"] = _valuation_inputs()
    if scenario_inputs:
        state.metadata["scenario_inputs"] = scenario_inputs
    return state


def test_scenario_agent_weights_default_bear_base_bull_cases() -> None:
    state = _scenario_state()

    ScenarioAnalysisAgent().run(state)

    report = state.metadata["scenario_report"]
    bear, base, bull = report.cases
    assert [case.probability for case in report.cases] == [0.25, 0.50, 0.25]
    assert bear.irr < base.irr < bull.irr
    expected = 0.25 * bear.irr + 0.5 * base.irr + 0.25 * bull.irr
    assert report.summary.probability_weighted_irr == pytest.approx(expected)
    assert report.capital_preservation_exit_multiple is not None
    assert report.sensitivity is not None
    assert len(report.sensitivity.cells) == 25


def test_scenario_agent_normalises_custom_probabilities_and_flags_capital_loss() -> None:
    state = _scenario_state(
        target_irr=0.25,
        scenarios=[
            {"name": "Crash", "probability": 1, "ebitda_multiplier": 0.3,
             "exit_multiple_delta": -5.0},
            {"name": "Base", "probability": 3},
        ],
    )

    ScenarioAnalysisAgent().run(state)

    report = state.metadata["scenario_report"]
    assert [case.probability for case in report.cases] == [0.25, 0.75]
    assert report.downside_capital_loss is True
    assert report.summary.resilience == ReturnResilience.FRAGILE
    assert report.summary.target_irr == 0.25


def test_scenario_agent_requires_lbo_inputs() -> None:
    with pytest.raises(ValueError, match="lbo"):
        ScenarioAnalysisAgent().run(AgentState(company_name="ExampleCo"))


def test_financial_agent_reads_roe_as_a_decimal() -> None:
    """Regression: ROE arrives as 0.25, so a >20 threshold rated every company Weak."""

    state = AgentState(company_name="ExampleCo", financial_data=_financial_data())

    FinancialAgent().run(state)

    report = state.metadata["financial_report"]
    assert state.ratios["roe"] == pytest.approx(0.25)
    assert report.summary.health == FinancialHealth.EXCELLENT
    assert report.metrics[0].value == pytest.approx(25.0)
    assert report.strengths and not report.weaknesses


def test_memo_covers_every_section_with_figures_from_the_reports() -> None:
    report = run_deal_analysis(
        DealAnalysisInputs(
            company_name="ExampleCo",
            financial_data=_financial_data(),
            valuation_inputs=_valuation_inputs(),
            industry_inputs=_industry_inputs(),
            risk_inputs={"altman_z": 3.2, "piotroski_score": 7, "industry_risk_score": 30},
            due_diligence_inputs=_due_diligence_inputs(),
        )
    )

    memo = report.investment_memo
    assert memo is not None
    assert [section.heading for section in memo.sections] == [
        "Executive Summary",
        "Company and Industry",
        "Financial Performance",
        "Valuation",
        "Returns and Scenarios",
        "Key Risks and Diligence",
        "Committee Decision",
        "Decision Rationale and Evidence",
        "Next Steps",
    ]
    lbo_irr = report.valuation_report.lbo_returns.irr
    assert f"{lbo_irr:.1%}" in memo.markdown
    assert memo.markdown.startswith("# Investment Memo: ExampleCo")
    assert "Red flag" in memo.markdown


def _distressed_financial_data(**overrides: float) -> dict:
    """A loss-making retailer whose losses have wiped out its equity."""

    data = _financial_data()
    values = {
        "net_income": -76.0,
        "shareholders_equity": -60.0,
        "ebit": -18.0,
        "interest_expense": 52.0,
        **overrides,
    }
    data["current"] = replace(data["current"], **values)
    return data


def test_negative_equity_is_distressed_not_excellent() -> None:
    """Regression: a net loss over negative equity is a positive ROE (-76 / -60 = 127%),
    which rated an insolvent company Excellent and counted as support for the deal."""

    state = AgentState(company_name="Castell", financial_data=_distressed_financial_data())

    FinancialAgent().run(state)

    report = state.metadata["financial_report"]
    assert state.ratios["roe"] > 1.0  # the misleading figure is still what the maths gives
    assert report.summary.health == FinancialHealth.DISTRESSED
    assert not report.strengths
    assert {item.title for item in report.weaknesses} == {
        "Negative shareholders' equity",
        "Net loss",
        "Operating profit does not cover interest",
    }
    assert report.recommendation.recommendation == "Negative"
    assert "equity is zero or negative" in report.summary.executive_summary
    assert any(finding.title == "ROE is not meaningful" for finding in report.findings)


def test_zero_equity_is_distressed_instead_of_crashing_the_analysis() -> None:
    data = _distressed_financial_data(shareholders_equity=0.0)
    state = AgentState(company_name="Castell", financial_data=data)

    FinancialAgent().run(state)

    assert state.metadata["financial_report"].summary.health == FinancialHealth.DISTRESSED


def test_a_net_loss_with_positive_equity_is_weak() -> None:
    data = _distressed_financial_data(shareholders_equity=400.0, ebit=60.0)
    state = AgentState(company_name="LossCo", financial_data=data)

    FinancialAgent().run(state)

    report = state.metadata["financial_report"]
    assert report.summary.health == FinancialHealth.WEAK
    assert [item.title for item in report.weaknesses] == ["Net loss"]


def test_distressed_financials_count_against_the_deal() -> None:
    report = run_deal_analysis(
        DealAnalysisInputs(
            company_name="Castell",
            financial_data=_distressed_financial_data(),
            valuation_inputs=_valuation_inputs(),
            industry_inputs=_industry_inputs(),
            risk_inputs={"altman_z": 3.2, "piotroski_score": 7, "industry_risk_score": 30},
            due_diligence_inputs=[],
        )
    )

    vote = next(
        item for item in report.ic_decision.committee_vote.votes if item.area == "Financial health"
    )
    assert vote.outcome == "CONCERN"
    assert report.final_recommendation != "BUY"

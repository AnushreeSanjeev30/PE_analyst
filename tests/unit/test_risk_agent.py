from types import SimpleNamespace

from agents import AgentState, RiskAgent
from pe_analyst.engines.financial.models import FinancialStatement


def test_risk_agent_scores_financial_and_valuation_risks() -> None:
    current = FinancialStatement(
        revenue=1_000.0,
        cost_of_goods_sold=600.0,
        ebitda=200.0,
        ebit=150.0,
        net_income=100.0,
        operating_cash_flow=140.0,
        capital_expenditure=40.0,
        total_assets=1_000.0,
        shareholders_equity=400.0,
        total_debt=800.0,
        interest_expense=80.0,
        current_assets=200.0,
        inventory=50.0,
        current_liabilities=180.0,
    )
    valuation = SimpleNamespace(lbo_returns=SimpleNamespace(irr=0.12))
    state = AgentState(
        company_name="ExampleCo",
        financial_data={"current": current},
        ratios={"current_ratio": 1.11, "debt_to_ebitda": 4.0},
        metadata={
            "valuation_report": valuation,
            "risk_inputs": {"altman_z": 1.5, "piotroski_score": 4, "industry_risk_score": 55},
        },
    )

    response = RiskAgent().run(state)

    report = response.metadata["report"]
    assert report.summary.score > 0
    assert any(factor.category == "Interest Coverage" for factor in report.factors)
    assert report.major_risks
    assert state.metadata["risk_report"] is report


def test_risk_agent_reports_missing_data_without_fabricating_it() -> None:
    state = AgentState(company_name="ExampleCo", ratios={"current_ratio": 2.0})

    report = RiskAgent().run(state).metadata["report"]

    assert "altman_z" in report.missing_data
    assert "valuation_report" in report.missing_data

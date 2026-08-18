from agents import DealAnalysisInputs, run_deal_analysis
from agents.orchestrator_models import RunStatus
from pe_analyst.engines.financial.models import FinancialStatement


def _financial_data() -> dict:
    current = FinancialStatement(
        revenue=1_000.0,
        cost_of_goods_sold=600.0,
        ebitda=220.0,
        ebit=150.0,
        net_income=100.0,
        operating_cash_flow=140.0,
        capital_expenditure=40.0,
        total_assets=1_000.0,
        shareholders_equity=400.0,
        total_debt=200.0,
        interest_expense=20.0,
        current_assets=200.0,
        inventory=50.0,
        current_liabilities=180.0,
    )
    previous = FinancialStatement(
        revenue=900.0,
        cost_of_goods_sold=560.0,
        ebitda=190.0,
        ebit=130.0,
        net_income=85.0,
        operating_cash_flow=120.0,
        capital_expenditure=35.0,
        total_assets=900.0,
        shareholders_equity=350.0,
        total_debt=210.0,
        interest_expense=22.0,
        current_assets=180.0,
        inventory=45.0,
        current_liabilities=170.0,
    )
    return {"current": current, "previous": previous}


def _valuation_inputs() -> dict:
    return {
        "current_price_per_share": 85.0,
        "dcf": {
            "revenue": 1_000.0,
            "assumptions": {
                "revenue_growth": 0.08,
                "ebit_margin": 0.20,
                "cash": 100.0,
                "debt": 200.0,
                "shares_outstanding": 10.0,
            },
        },
        "comparables": {
            "target": {
                "revenue": 1_000.0,
                "ebitda": 220.0,
                "cash": 100.0,
                "debt": 200.0,
                "shares_outstanding": 10.0,
            },
            "peers": [
                {
                    "name": "Peer A",
                    "enterprise_value": 1_800.0,
                    "market_cap": 1_600.0,
                    "revenue": 200.0,
                    "ebitda": 40.0,
                    "net_income": 20.0,
                    "book_value": 200.0,
                },
                {
                    "name": "Peer B",
                    "enterprise_value": 2_000.0,
                    "market_cap": 1_750.0,
                    "revenue": 250.0,
                    "ebitda": 50.0,
                    "net_income": 25.0,
                    "book_value": 225.0,
                },
                {
                    "name": "Peer C",
                    "enterprise_value": 1_650.0,
                    "market_cap": 1_400.0,
                    "revenue": 220.0,
                    "ebitda": 44.0,
                    "net_income": 22.0,
                    "book_value": 180.0,
                },
            ],
        },
        "lbo": {
            "assumptions": {"purchase_price": 1_600.0, "holding_period": 5, "exit_multiple": 8.0},
            "operating_projection": [
                {
                    "year": year,
                    "revenue": 1_000.0 + year * 60,
                    "ebitda": 220.0 + year * 15,
                    "taxes": 30.0 + year,
                    "capex": 30.0 + year,
                    "change_in_nwc": 10.0 + year,
                }
                for year in range(1, 6)
            ],
        },
    }


def _industry_inputs() -> dict:
    return {
        "industry_name": "Vertical Software",
        "market_growth_pct": 0.12,
        "competitive_position": "Strong",
        "competitors": [
            {"name": "Peer A", "market_share_pct": 18.0, "positioning": "Enterprise leader"},
        ],
        "porter_forces": {"rivalry": 4, "buyer_power": 3},
        "management_themes": ["Cross-sell expansion"],
        "evidence": [
            {
                "topic": "market",
                "source": "2025 Annual Report",
                "page_number": 12,
                "excerpt": "Market demand remains strong.",
                "claim": "Management expects durable demand.",
                "confidence": 0.9,
            },
            {
                "topic": "competition",
                "source": "2025 Annual Report",
                "page_number": 18,
                "excerpt": "The market is fragmented.",
                "claim": "Fragmentation supports consolidation.",
                "confidence": 0.85,
            },
            {
                "topic": "management",
                "source": "2025 Annual Report",
                "page_number": 26,
                "excerpt": "We are investing in sales capacity.",
                "claim": "Management is funding growth capacity.",
                "confidence": 0.8,
            },
        ],
    }


def test_run_deal_analysis_completes_all_stages_and_returns_a_unified_report() -> None:
    inputs = DealAnalysisInputs(
        company_name="ExampleCo",
        financial_data=_financial_data(),
        valuation_inputs=_valuation_inputs(),
        industry_inputs=_industry_inputs(),
        risk_inputs={"altman_z": 3.2, "piotroski_score": 7, "industry_risk_score": 30},
    )

    report = run_deal_analysis(inputs)

    assert report.status == RunStatus.COMPLETED
    assert report.failed_stage is None
    assert report.error is None
    assert [record.stage for record in report.stages] == [
        "financial",
        "valuation",
        "risk",
        "industry",
        "investment_committee",
    ]
    assert all(record.status == RunStatus.COMPLETED for record in report.stages)
    assert report.financial_report is not None
    assert report.valuation_report is not None
    assert report.risk_report is not None
    assert report.industry_report is not None
    assert report.investment_committee_report is not None
    assert report.final_recommendation in {"BUY", "HOLD", "REJECT"}
    assert report.investment_committee_report.summary.recommendation == report.final_recommendation


def test_run_deal_analysis_fails_fast_and_keeps_completed_reports() -> None:
    inputs = DealAnalysisInputs(
        company_name="ExampleCo",
        financial_data=_financial_data(),
        valuation_inputs={},
        industry_inputs=_industry_inputs(),
    )

    report = run_deal_analysis(inputs)

    assert report.status == RunStatus.FAILED
    assert report.failed_stage == "valuation"
    assert "valuation" in report.error.lower()
    assert report.financial_report is not None
    assert report.valuation_report is None
    assert report.risk_report is None
    assert report.industry_report is None
    assert report.investment_committee_report is None
    assert [record.status for record in report.stages] == [
        RunStatus.COMPLETED,
        RunStatus.FAILED,
        RunStatus.SKIPPED,
        RunStatus.SKIPPED,
        RunStatus.SKIPPED,
    ]

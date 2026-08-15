from agents import AgentState, ValuationAgent


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
                    "year": 1,
                    "revenue": 1_060.0,
                    "ebitda": 220.0,
                    "taxes": 30.0,
                    "capex": 30.0,
                    "change_in_nwc": 10.0,
                },
                {
                    "year": 2,
                    "revenue": 1_124.0,
                    "ebitda": 235.0,
                    "taxes": 32.0,
                    "capex": 32.0,
                    "change_in_nwc": 11.0,
                },
                {
                    "year": 3,
                    "revenue": 1_191.0,
                    "ebitda": 250.0,
                    "taxes": 34.0,
                    "capex": 34.0,
                    "change_in_nwc": 12.0,
                },
                {
                    "year": 4,
                    "revenue": 1_262.0,
                    "ebitda": 266.0,
                    "taxes": 36.0,
                    "capex": 36.0,
                    "change_in_nwc": 13.0,
                },
                {
                    "year": 5,
                    "revenue": 1_338.0,
                    "ebitda": 283.0,
                    "taxes": 38.0,
                    "capex": 38.0,
                    "change_in_nwc": 14.0,
                },
            ],
        },
    }


def test_valuation_agent_runs_all_three_methods_and_updates_state() -> None:
    state = AgentState(company_name="ExampleCo", metadata={"valuation_inputs": _valuation_inputs()})

    response = ValuationAgent().run(state)

    report = response.metadata["report"]
    assert response.agent_name == "Valuation Agent"
    assert report.summary.intrinsic_value_per_share is not None
    assert report.summary.fair_value_per_share is not None
    assert report.lbo_returns is not None
    assert report.lbo_returns.irr > 0
    assert set(state.valuation) == {"dcf", "comparables", "lbo", "report"}
    assert state.metadata["valuation_report"] is report
    assert len(state.conversation_history) == 1


def test_valuation_agent_requires_all_valuation_methods() -> None:
    state = AgentState(company_name="ExampleCo", metadata={"valuation_inputs": {}})

    try:
        ValuationAgent().run(state)
    except ValueError as error:
        assert "comparables" in str(error)
    else:
        raise AssertionError("Expected incomplete valuation input to be rejected")

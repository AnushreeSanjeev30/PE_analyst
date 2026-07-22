from pe_analyst.valuation import DCFEngine, ValuationAssumptions


def test_dcf_returns_positive_value():
    engine = DCFEngine(ValuationAssumptions())
    result = engine.calculate(1_000_000)

    assert result.enterprise_value > 0
    assert result.equity_value > 0
    assert result.price_per_share > 0

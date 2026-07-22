from pe_analyst.valuation import DCFEngine, ValuationAssumptions


def test_dcf_returns_positive_value():
    engine = DCFEngine(ValuationAssumptions())
    ev = engine.enterprise_value(1_000_000)

    assert ev > 0

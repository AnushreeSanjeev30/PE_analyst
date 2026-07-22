from pe_analyst.valuation import TerminalValueEngine


def test_gordon_growth_positive():
    assert (
        TerminalValueEngine.gordon_growth(
            100,
            0.10,
            0.03,
        )
        > 0
    )

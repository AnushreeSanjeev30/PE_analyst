from pe_analyst.valuation import MultiplesEngine


def test_ev_ebitda():
    assert MultiplesEngine.ev_ebitda(100, 10) == 10


def test_ev_revenue():
    assert MultiplesEngine.ev_revenue(100, 20) == 5


def test_pe():
    assert MultiplesEngine.pe(40, 4) == 10

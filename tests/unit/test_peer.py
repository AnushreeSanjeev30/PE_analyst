from pe_analyst.valuation import PeerCompany


def test_peer_company_multiples():
    peer = PeerCompany(
        name="Test",
        enterprise_value=1000,
        market_cap=800,
        revenue=200,
        ebitda=100,
        net_income=50,
        book_value=400,
    )

    assert peer.ev_revenue == 5
    assert peer.ev_ebitda == 10
    assert peer.pe == 16
    assert peer.price_to_book == 2

from pathlib import Path

import httpx
import pytest

from pe_analyst.core.config import Settings
from pe_analyst.deals.api import resolve_peers
from pe_analyst.market_data import (
    AlphaVantageMarketDataProvider,
    MarketDataProviderError,
    build_market_data_provider,
)

OVERVIEW = {
    "Symbol": "IBM",
    "Name": "International Business Machines",
    "MarketCapitalization": "243661603000",
    "EBITDA": "16634000000",
    "BookValue": "37.6",
    "ProfitMargin": "0.16",
    "RevenueTTM": "69868003000",
    "EVToRevenue": "4.29",
    "EVToEBITDA": "16.9",
    "SharesOutstanding": "945121000",
}


def _provider(handler: object, cache_dir: Path | None = None) -> AlphaVantageMarketDataProvider:
    client = httpx.Client(
        base_url="https://www.alphavantage.co",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )
    return AlphaVantageMarketDataProvider("key", cache_dir=cache_dir, client=client)


def test_overview_is_mapped_onto_peer_company() -> None:
    peer = _provider(lambda request: httpx.Response(200, json=OVERVIEW)).get_comparable_companies(
        "ibm"
    )[0]

    assert peer.name == "International Business Machines"
    assert peer.enterprise_value == pytest.approx(4.29 * 69_868_003_000)
    assert peer.net_income == pytest.approx(0.16 * 69_868_003_000)
    assert peer.book_value == pytest.approx(37.6 * 945_121_000)
    assert peer.ev_ebitda == pytest.approx(peer.enterprise_value / 16_634_000_000)


def test_rate_limit_message_is_an_error_not_data() -> None:
    provider = _provider(
        lambda request: httpx.Response(200, json={"Information": "rate limit is 25 requests"})
    )

    with pytest.raises(MarketDataProviderError, match="rate limit"):
        provider.get_comparable_companies("IBM")


def test_responses_are_cached_on_disk(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["symbol"])
        return httpx.Response(200, json=OVERVIEW)

    provider = _provider(handler, cache_dir=tmp_path)
    provider.get_comparable_companies("IBM")
    provider.get_comparable_companies("IBM")

    assert calls == ["IBM"]


def test_free_text_industry_is_rejected_with_guidance() -> None:
    provider = _provider(lambda request: httpx.Response(200, json=OVERVIEW))

    with pytest.raises(MarketDataProviderError, match="tickers"):
        provider.get_comparable_companies("Vertical Software")


def test_factory_builds_alphavantage_and_requires_a_key(test_settings: Settings) -> None:
    configured = test_settings.model_copy(
        update={"market_data_provider": "alphavantage", "market_data_api_key": "k"}
    )
    assert isinstance(build_market_data_provider(configured), AlphaVantageMarketDataProvider)

    with pytest.raises(MarketDataProviderError, match="MARKET_DATA_API_KEY"):
        build_market_data_provider(configured.model_copy(update={"market_data_api_key": None}))


def test_resolve_peers_keeps_explicit_peers_and_reports_unconfigured_vendor(
    test_settings: Settings,
) -> None:
    explicit = {"comparables": {"peers": [{"name": "A"}], "peer_tickers": ["IBM"]}}
    assert resolve_peers(explicit, test_settings) is explicit

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        resolve_peers({"comparables": {"peer_tickers": ["IBM"]}}, test_settings)
    assert error.value.status_code == 422

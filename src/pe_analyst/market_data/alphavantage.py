"""Alpha Vantage comparable-company data (free tier: alphavantage.co/support/#api-key).

Alpha Vantage has no "find peers" endpoint, so ``industry_or_ticker`` is a comma-separated list
of peer tickers chosen by the analyst (e.g. ``"MSFT,ORCL,SAP"``). Each ticker's ``OVERVIEW``
gives trailing-twelve-month figures, which are mapped onto :class:`PeerCompany`:

* enterprise value = ``EVToRevenue`` x ``RevenueTTM`` (falls back to ``EVToEBITDA`` x ``EBITDA``)
* net income       = ``ProfitMargin`` x ``RevenueTTM``
* book value       = ``BookValue`` (per share) x ``SharesOutstanding``

The free tier allows ~25 requests/day, so responses are cached on disk.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from pe_analyst.valuation.peer import PeerCompany

from .exceptions import MarketDataProviderError
from .provider import MarketDataProvider

_TICKER = re.compile(r"^[A-Z0-9.\-]{1,12}$")


def _number(overview: dict[str, Any], key: str) -> float | None:
    raw: Any = overview.get(key)
    if raw in (None, "", "None", "-"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def overview_to_peer(overview: dict[str, Any]) -> PeerCompany:
    revenue = _number(overview, "RevenueTTM")
    ebitda = _number(overview, "EBITDA")
    market_cap = _number(overview, "MarketCapitalization")
    if revenue is None or market_cap is None:
        raise MarketDataProviderError(
            f"Alpha Vantage overview for {overview.get('Symbol')} lacks revenue or market cap"
        )
    ev_revenue = _number(overview, "EVToRevenue")
    ev_ebitda = _number(overview, "EVToEBITDA")
    if ev_revenue is not None:
        enterprise_value = ev_revenue * revenue
    elif ev_ebitda is not None and ebitda is not None:
        enterprise_value = ev_ebitda * ebitda
    else:
        enterprise_value = market_cap
    margin = _number(overview, "ProfitMargin") or 0.0
    book_per_share = _number(overview, "BookValue") or 0.0
    shares = _number(overview, "SharesOutstanding") or 0.0
    return PeerCompany(
        name=str(overview.get("Name") or overview.get("Symbol")),
        enterprise_value=enterprise_value,
        market_cap=market_cap,
        revenue=revenue,
        ebitda=ebitda or 0.0,
        net_income=margin * revenue,
        book_value=book_per_share * shares,
    )


class AlphaVantageMarketDataProvider(MarketDataProvider):
    base_url = "https://www.alphavantage.co"

    def __init__(
        self,
        api_key: str | None,
        *,
        cache_dir: Path | None = None,
        cache_ttl_hours: float = 24.0,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise MarketDataProviderError(
                "MARKET_DATA_API_KEY is required for MARKET_DATA_PROVIDER=alphavantage"
            )
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_ttl_seconds = cache_ttl_hours * 3600
        self.client = client or httpx.Client(base_url=self.base_url, timeout=timeout_seconds)

    def get_comparable_companies(self, industry_or_ticker: str) -> list[PeerCompany]:
        tickers = [item.strip().upper() for item in industry_or_ticker.split(",") if item.strip()]
        if not tickers:
            raise MarketDataProviderError("Provide comma-separated peer tickers, e.g. 'MSFT,ORCL'")
        invalid = [ticker for ticker in tickers if not _TICKER.match(ticker)]
        if invalid:
            raise MarketDataProviderError(
                f"Alpha Vantage needs peer tickers, not free text; invalid: {', '.join(invalid)}"
            )
        return [overview_to_peer(self.overview(ticker)) for ticker in tickers]

    def overview(self, ticker: str) -> dict[str, Any]:
        cached = self._read_cache(ticker)
        if cached is not None:
            return cached
        try:
            response = self.client.get(
                "/query", params={"function": "OVERVIEW", "symbol": ticker, "apikey": self.api_key}
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise MarketDataProviderError(
                f"Alpha Vantage request for {ticker} failed: {error}"
            ) from error
        # Rate limits and bad keys come back as HTTP 200 with a message instead of data.
        for key in ("Error Message", "Information", "Note"):
            if key in body:
                raise MarketDataProviderError(f"Alpha Vantage ({ticker}): {body[key]}")
        if not body.get("Symbol"):
            raise MarketDataProviderError(f"Alpha Vantage has no overview for ticker {ticker}")
        self._write_cache(ticker, body)
        return dict(body)

    def _cache_path(self, ticker: str) -> Path | None:
        return self.cache_dir / f"alphavantage_overview_{ticker}.json" if self.cache_dir else None

    def _read_cache(self, ticker: str) -> dict[str, Any] | None:
        path = self._cache_path(ticker)
        if path is None or not path.is_file():
            return None
        if time.time() - path.stat().st_mtime > self.cache_ttl_seconds:
            return None
        try:
            return dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return None

    def _write_cache(self, ticker: str, body: dict[str, Any]) -> None:
        path = self._cache_path(ticker)
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(body), encoding="utf-8")
        except OSError:
            pass


__all__ = ["AlphaVantageMarketDataProvider", "overview_to_peer"]

"""Yahoo Finance — unofficial, undocumented, no API key. Chosen specifically
for NSE/BSE (Indian) coverage: Finnhub and Twelve Data both gate Indian
equities behind a paid plan, but Yahoo's public chart endpoint serves real
NSE/BSE quotes and historical OHLCV for free, no signup.

Two very different reliability tiers here, by design:

- `/v8/finance/chart/{symbol}` (quotes, history, basic company info) needs
  no auth beyond a browser-like User-Agent — verified reliable across many
  real calls during development.
- `/v10/finance/quoteSummary/{symbol}` (fundamentals, analyst ratings) is
  gated by Yahoo's anti-bot "crumb" token, which requires a session cookie
  first and has been observed to intermittently reject that cookie even
  moments after it was issued. Rather than fabricate fundamentals when this
  fails, every crumb-gated method degrades to an empty result — the same
  "explicit gap, never invented data" convention this codebase already uses
  for AI-report sections and missing technicals.

This is exactly the tradeoff communicated to the user before choosing this
vendor: real data when it works, honest absence when Yahoo's undocumented
anti-bot layer blocks a request, never a made-up substitute.
"""
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.core.errors import ExternalServiceError
from app.domain.market.price import PriceInterval
from app.domain.ports.market_data_source import CompanyInfo, Quote, RawNewsItem, RawPriceBar, SymbolMatch

_INDIAN_EXCHANGES = {"NSI", "BSE"}  # Yahoo's own exchange codes for NSE/BSE

_INTERVAL_MAP = {
    PriceInterval.M1: "1m",
    PriceInterval.M5: "5m",
    PriceInterval.H1: "60m",
    PriceInterval.D1: "1d",
}
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-platform/1.0)"}


class YahooFinanceMarketDataSource:
    name = "yahoo_finance"
    _chart_base = "https://query1.finance.yahoo.com/v8/finance/chart"
    _quote_summary_base = "https://query1.finance.yahoo.com/v10/finance/quoteSummary"
    _crumb_url = "https://query1.finance.yahoo.com/v1/test/getcrumb"
    _search_url = "https://query1.finance.yahoo.com/v1/finance/search"

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport  # only ever set by tests
        # One persistent client (not a fresh one per call, unlike the other
        # adapters) so the crumb flow's session cookie actually survives
        # between the cookie-issuing call and the request that uses it.
        self._client = httpx.AsyncClient(timeout=15.0, transport=transport, headers=_HEADERS)
        self._crumb: str | None = None

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---- reliable: no auth beyond a User-Agent -----------------------------

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        quotes: list[Quote] = []
        for symbol in symbols:
            meta = await self._chart_meta(symbol)
            if meta is None or not meta.get("regularMarketPrice"):
                continue
            price = Decimal(str(meta["regularMarketPrice"]))
            prev_close = Decimal(str(meta.get("chartPreviousClose") or meta["regularMarketPrice"]))
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else Decimal("0")
            quotes.append(
                Quote(
                    symbol=symbol, price=price, change_pct=change_pct,
                    volume=Decimal(str(meta.get("regularMarketVolume", 0))),
                    ts=datetime.fromtimestamp(meta.get("regularMarketTime", 0), tz=UTC),
                    open=self._decimal_or_none(meta.get("regularMarketOpen")),
                    high=self._decimal_or_none(meta.get("regularMarketDayHigh")),
                    low=self._decimal_or_none(meta.get("regularMarketDayLow")),
                )
            )
        return quotes

    async def get_history(
        self, symbol: str, interval: PriceInterval, start: date, end: date
    ) -> list[RawPriceBar]:
        params = {
            "interval": _INTERVAL_MAP[interval],
            "period1": int(datetime.combine(start, datetime.min.time(), tzinfo=UTC).timestamp()),
            "period2": int(datetime.combine(end, datetime.min.time(), tzinfo=UTC).timestamp()),
        }
        resp = await self._client.get(f"{self._chart_base}/{symbol}", params=params)
        if resp.status_code != 200:
            raise ExternalServiceError(f"yahoo_finance chart failed: {resp.status_code}", {"body": resp.text[:500]})

        result = resp.json().get("chart", {}).get("result")
        if not result:
            return []
        payload = result[0]
        timestamps = payload.get("timestamp") or []
        quote = (payload.get("indicators", {}).get("quote") or [{}])[0]
        bars = []
        for i, ts in enumerate(timestamps):
            keys = ("open", "high", "low", "close", "volume")
            o, h, low, c, v = (quote.get(k, [None] * len(timestamps))[i] for k in keys)
            if None in (o, h, low, c):
                continue  # Yahoo pads gaps (holidays/halts) with nulls
            bars.append(
                RawPriceBar(
                    symbol=symbol, ts=datetime.fromtimestamp(ts, tz=UTC), interval=interval,
                    open=Decimal(str(o)), high=Decimal(str(h)), low=Decimal(str(low)),
                    close=Decimal(str(c)), volume=Decimal(str(v or 0)),
                )
            )
        return bars

    async def get_company_info(self, symbol: str) -> CompanyInfo | None:
        meta = await self._chart_meta(symbol)
        if meta is None or not meta.get("longName"):
            return None
        return CompanyInfo(
            symbol=symbol, name=meta.get("longName", meta.get("shortName", symbol)),
            exchange=meta.get("fullExchangeName", ""), currency=meta.get("currency", "USD"),
        )

    async def _chart_meta(self, symbol: str) -> dict[str, Any] | None:
        resp = await self._client.get(f"{self._chart_base}/{symbol}", params={"range": "5d", "interval": "1d"})
        if resp.status_code != 200:
            raise ExternalServiceError(f"yahoo_finance chart failed: {resp.status_code}", {"body": resp.text[:500]})
        result = resp.json().get("chart", {}).get("result")
        return result[0].get("meta") if result else None

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        return Decimal(str(value)) if value is not None else None

    # ---- best-effort: gated by Yahoo's undocumented crumb mechanism -------

    async def _crumb_or_none(self) -> str | None:
        if self._crumb is not None:
            return self._crumb
        try:
            resp = await self._client.get(self._crumb_url)
            if resp.status_code == 200 and resp.text and "error" not in resp.text.lower():
                self._crumb = resp.text.strip()
                return self._crumb
        except httpx.HTTPError:
            pass
        return None

    async def _quote_summary(self, symbol: str, modules: str) -> dict[str, Any]:
        crumb = await self._crumb_or_none()
        if crumb is None:
            return {}
        resp = await self._client.get(
            f"{self._quote_summary_base}/{symbol}", params={"modules": modules, "crumb": crumb}
        )
        if resp.status_code != 200:
            return {}
        result = resp.json().get("quoteSummary", {}).get("result")
        if not result:
            self._crumb = None  # likely a stale/rejected crumb — refetch next time
            return {}
        return result[0]

    async def get_fundamentals_raw(self, symbol: str) -> dict[str, Any]:
        data = await self._quote_summary(symbol, "defaultKeyStatistics,financialData,summaryProfile")
        merged: dict[str, Any] = {}
        for module in ("defaultKeyStatistics", "financialData", "summaryProfile"):
            merged.update(data.get(module) or {})
        return merged

    async def get_analyst_ratings(self, symbol: str) -> list[dict[str, Any]]:
        data = await self._quote_summary(symbol, "recommendationTrend")
        trend = (data.get("recommendationTrend") or {}).get("trend") or []
        return list(trend)

    async def get_insider_trades(self, symbol: str) -> list[dict[str, Any]]:
        data = await self._quote_summary(symbol, "insiderTransactions")
        return list((data.get("insiderTransactions") or {}).get("transactions") or [])

    # ---- news: not this vendor's job — see CompositeMarketDataSource ------

    async def get_news(
        self, symbols: list[str], limit: int = 50, *, name_by_symbol: dict[str, str] | None = None
    ) -> list[RawNewsItem]:
        return []

    # ---- symbol search: reliable, no auth beyond a User-Agent -------------

    async def search_symbols(self, query: str) -> list[SymbolMatch]:
        resp = await self._client.get(self._search_url, params={"q": query, "quotesCount": 15, "newsCount": 0})
        if resp.status_code != 200:
            raise ExternalServiceError(f"yahoo_finance search failed: {resp.status_code}", {"body": resp.text[:500]})
        quotes = resp.json().get("quotes", [])
        return [
            SymbolMatch(
                symbol=q["symbol"], name=q.get("shortname") or q.get("longname") or q["symbol"],
                exchange=q["exchange"],
            )
            for q in quotes
            if q.get("exchange") in _INDIAN_EXCHANGES and q.get("quoteType") == "EQUITY" and q.get("symbol")
        ]

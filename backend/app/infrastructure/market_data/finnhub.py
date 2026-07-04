"""Finnhub adapter — covers every MarketDataSource method on Finnhub's free
tier: quotes, candles (history), company profile, company news, basic
financials (fundamentals), analyst recommendation trends, and insider
transactions. Real REST calls, no SDK — mirrors the AI provider adapters'
httpx + injectable-transport pattern for the same reason: testable without
a live key or network.
"""
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.core.errors import ExternalServiceError
from app.domain.market.price import PriceInterval
from app.domain.ports.market_data_source import CompanyInfo, Quote, RawNewsItem, RawPriceBar, SymbolMatch

_RESOLUTION_BY_INTERVAL = {
    PriceInterval.M1: "1",
    PriceInterval.M5: "5",
    PriceInterval.H1: "60",
    PriceInterval.D1: "D",
}


class FinnhubMarketDataSource:
    name = "finnhub"
    base_url = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str, *, transport: httpx.BaseTransport | None = None) -> None:
        if not api_key:
            raise ExternalServiceError("finnhub: missing API key")
        self._api_key = api_key
        self._transport = transport  # only ever set by tests

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=15.0, transport=self._transport) as client:
            resp = await client.get(
                f"{self.base_url}{path}", params={**params, "token": self._api_key}
            )
        if resp.status_code != 200:
            raise ExternalServiceError(f"finnhub {path} failed: {resp.status_code}", {"body": resp.text[:500]})
        return resp.json()

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        quotes: list[Quote] = []
        for symbol in symbols:
            data = await self._get("/quote", {"symbol": symbol})
            if not data or data.get("c") in (None, 0):
                continue
            current, prev_close = Decimal(str(data["c"])), Decimal(str(data.get("pc") or data["c"]))
            change_pct = ((current - prev_close) / prev_close * 100) if prev_close else Decimal("0")
            quotes.append(
                Quote(
                    symbol=symbol, price=current, change_pct=change_pct,
                    volume=Decimal("0"), ts=datetime.fromtimestamp(data.get("t", 0), tz=UTC),
                    open=Decimal(str(data["o"])) if data.get("o") else None,
                    high=Decimal(str(data["h"])) if data.get("h") else None,
                    low=Decimal(str(data["l"])) if data.get("l") else None,
                )
            )
        return quotes

    async def get_history(
        self, symbol: str, interval: PriceInterval, start: date, end: date
    ) -> list[RawPriceBar]:
        resolution = _RESOLUTION_BY_INTERVAL[interval]
        params = {
            "symbol": symbol, "resolution": resolution,
            "from": int(datetime.combine(start, datetime.min.time()).timestamp()),
            "to": int(datetime.combine(end, datetime.min.time()).timestamp()),
        }
        data = await self._get("/stock/candle", params)
        if data.get("s") != "ok":
            return []
        return [
            RawPriceBar(
                symbol=symbol, ts=datetime.fromtimestamp(t, tz=UTC), interval=interval,
                open=Decimal(str(o)), high=Decimal(str(h)), low=Decimal(str(low)),
                close=Decimal(str(c)), volume=Decimal(str(v)),
            )
            for t, o, h, low, c, v in zip(
                data["t"], data["o"], data["h"], data["l"], data["c"], data["v"], strict=True
            )
        ]

    async def get_company_info(self, symbol: str) -> CompanyInfo | None:
        data = await self._get("/stock/profile2", {"symbol": symbol})
        if not data or not data.get("name"):
            return None
        market_cap = Decimal(str(data["marketCapitalization"])) * Decimal("1000000") if data.get(
            "marketCapitalization"
        ) else None
        return CompanyInfo(
            symbol=symbol, name=data["name"], exchange=data.get("exchange", ""),
            industry=data.get("finnhubIndustry", ""), country=data.get("country", ""),
            currency=data.get("currency", "USD"), market_cap=market_cap,
        )

    async def get_news(
        self, symbols: list[str], limit: int = 50, *, name_by_symbol: dict[str, str] | None = None
    ) -> list[RawNewsItem]:
        # Finnhub's /company-news is ticker-based and already date-scoped, so
        # name_by_symbol (needed for marketaux's plain keyword search) doesn't apply here.
        today = date.today()
        month_ago = today.replace(day=1)
        items: list[RawNewsItem] = []
        for symbol in symbols:
            data = await self._get(
                "/company-news", {"symbol": symbol, "from": month_ago.isoformat(), "to": today.isoformat()}
            )
            for raw in data[:limit]:
                items.append(
                    RawNewsItem(
                        source=raw.get("source", ""), url=raw.get("url", ""),
                        title=raw.get("headline", ""), content=raw.get("summary", ""),
                        published_at=(
                            datetime.fromtimestamp(raw["datetime"], tz=UTC)
                            if raw.get("datetime") else None
                        ),
                        symbols=(symbol,),
                    )
                )
        return items

    async def get_fundamentals_raw(self, symbol: str) -> dict[str, Any]:
        data = await self._get("/stock/metric", {"symbol": symbol, "metric": "all"})
        return data.get("metric", {})

    async def get_analyst_ratings(self, symbol: str) -> list[dict[str, Any]]:
        return await self._get("/stock/recommendation", {"symbol": symbol})

    async def get_insider_trades(self, symbol: str) -> list[dict[str, Any]]:
        data = await self._get("/stock/insider-transactions", {"symbol": symbol})
        return data.get("data", [])

    async def search_symbols(self, query: str) -> list[SymbolMatch]:
        data = await self._get("/search", {"q": query})
        return [
            SymbolMatch(symbol=r["symbol"], name=r.get("description", r["symbol"]))
            for r in data.get("result", [])
            if r.get("type") == "Common Stock" and r.get("symbol")
        ]

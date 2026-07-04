"""marketaux — a financial-news-specific API, used only for its /news/all
endpoint. Everything else (quotes, history, fundamentals) stays on whichever
vendor covers that market; see CompositeMarketDataSource.

Free tier is a tight 100 requests/day, so this only ever makes one request
per symbol per call — no batching multiple symbols into one `search=`
query, because marketaux doesn't report which of several OR'd terms matched
a given article, and losing that per-company attribution would break the
Company page's News tab.

NSE-listed symbols aren't in marketaux's entity database (the `symbols=`
param returns nothing for them), and a plain keyword search on the raw
Yahoo-style ticker (e.g. "HDFCBANK.NS") almost never matches real article
text — that literal suffix just doesn't appear in prose. Real news refers
to companies by name ("HDFC Bank", "Reliance"), so the caller should pass
`name_by_symbol` (built from the already-resolved Company rows) wherever
possible; this only falls back to the bare, suffix-stripped ticker when no
name is given.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.errors import ExternalServiceError
from app.domain.ports.market_data_source import RawNewsItem

_MAX_ARTICLE_AGE_DAYS = 30  # a plain keyword search has no recency bias by
# default and will happily surface a years-old article that just happens to
# rank well on relevance — this keeps "trending news" actually recent.


class MarketauxNewsSource:
    name = "marketaux"
    base_url = "https://api.marketaux.com/v1"

    def __init__(
        self, api_key: str, *, countries: str | None = None, transport: httpx.BaseTransport | None = None
    ) -> None:
        if not api_key:
            raise ExternalServiceError("marketaux: missing API key")
        self._api_key = api_key
        self._countries = countries
        self._transport = transport  # only ever set by tests

    async def get_news(
        self, symbols: list[str], limit: int = 50, *, name_by_symbol: dict[str, str] | None = None
    ) -> list[RawNewsItem]:
        items: list[RawNewsItem] = []
        per_symbol = max(1, limit // max(1, len(symbols)))
        for symbol in symbols:
            query = (name_by_symbol or {}).get(symbol) or self._strip_suffix(symbol)
            items.extend(await self._get_for_symbol(symbol, query, per_symbol))
        return items

    @staticmethod
    def _strip_suffix(symbol: str) -> str:
        return symbol.removesuffix(".NS").removesuffix(".BO")

    async def _get_for_symbol(self, symbol: str, query: str, limit: int) -> list[RawNewsItem]:
        published_after = (datetime.now(UTC) - timedelta(days=_MAX_ARTICLE_AGE_DAYS)).date().isoformat()
        params: dict[str, Any] = {
            "search": query, "limit": limit, "api_token": self._api_key,
            "sort": "published_desc", "published_after": published_after,
        }
        if self._countries:
            params["countries"] = self._countries

        async with httpx.AsyncClient(timeout=15.0, transport=self._transport) as client:
            resp = await client.get(f"{self.base_url}/news/all", params=params)
        if resp.status_code != 200:
            raise ExternalServiceError(f"marketaux news failed: {resp.status_code}", {"body": resp.text[:500]})

        data = resp.json()
        return [
            RawNewsItem(
                source=raw.get("source", ""), url=raw.get("url", ""),
                title=raw.get("title", ""), content=raw.get("description") or raw.get("snippet", ""),
                published_at=self._parse_ts(raw.get("published_at")),
                symbols=(symbol,),
            )
            for raw in data.get("data", [])
        ]

    @staticmethod
    def _parse_ts(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return None

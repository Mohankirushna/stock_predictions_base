"""Composes market-data vendors per-capability rather than per-provider:
quotes/history/fundamentals/etc. come from `primary`, but news is delegated
to a dedicated news vendor when configured. Mirrors the AI provider router's
"never hardcode a single vendor" philosophy — MarketDataSource is a port,
and different capabilities can be best served by different real vendors.

Throttles the news vendor via the shared Cache port: a free-tier news API
typically has a much tighter daily quota than the primary quote/history
vendor, so re-fetching a symbol's news on every data-collection tick would
exhaust it in minutes. A symbol's news is fetched at most once per
`min_interval_hours`; a request within that window returns [] rather than
spending a call for an empty diff.
"""
from datetime import UTC, date, datetime
from typing import Any, Protocol

from app.domain.market.price import PriceInterval
from app.domain.ports.cache import Cache
from app.domain.ports.market_data_source import (
    CompanyInfo,
    MarketDataSource,
    Quote,
    RawNewsItem,
    RawPriceBar,
    SymbolMatch,
)

_THROTTLE_KEY_TTL_SLACK_SECONDS = 300  # cache TTL slightly outlives the throttle window


class NewsSource(Protocol):
    async def get_news(
        self, symbols: list[str], limit: int = 50, *, name_by_symbol: dict[str, str] | None = None
    ) -> list[RawNewsItem]: ...


class CompositeMarketDataSource:
    def __init__(
        self,
        primary: MarketDataSource,
        *,
        news_source: NewsSource | None = None,
        cache: Cache | None = None,
        news_min_interval_hours: int = 4,
    ) -> None:
        self._primary = primary
        self._news_source = news_source
        self._cache = cache
        self._news_min_interval_hours = news_min_interval_hours
        self.name = f"composite({getattr(primary, 'name', 'primary')}+{getattr(news_source, 'name', 'none')})"

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        return await self._primary.get_quotes(symbols)

    async def get_history(
        self, symbol: str, interval: PriceInterval, start: date, end: date
    ) -> list[RawPriceBar]:
        return await self._primary.get_history(symbol, interval, start, end)

    async def get_company_info(self, symbol: str) -> CompanyInfo | None:
        return await self._primary.get_company_info(symbol)

    async def get_fundamentals_raw(self, symbol: str) -> dict[str, Any]:
        return await self._primary.get_fundamentals_raw(symbol)

    async def get_analyst_ratings(self, symbol: str) -> list[dict[str, Any]]:
        return await self._primary.get_analyst_ratings(symbol)

    async def get_insider_trades(self, symbol: str) -> list[dict[str, Any]]:
        return await self._primary.get_insider_trades(symbol)

    async def search_symbols(self, query: str) -> list[SymbolMatch]:
        return await self._primary.search_symbols(query)

    async def get_news(
        self, symbols: list[str], limit: int = 50, *, name_by_symbol: dict[str, str] | None = None
    ) -> list[RawNewsItem]:
        if self._news_source is None:
            return await self._primary.get_news(symbols, limit, name_by_symbol=name_by_symbol)

        due = [s for s in symbols if await self._due_for_news(s)]
        if not due:
            return []
        items = await self._news_source.get_news(due, limit, name_by_symbol=name_by_symbol)
        for symbol in due:
            await self._mark_fetched(symbol)
        return items

    async def _due_for_news(self, symbol: str) -> bool:
        if self._cache is None:
            return True
        last = await self._cache.get(f"news_fetch:{symbol}")
        if last is None:
            return True
        elapsed_hours = (datetime.now(UTC) - datetime.fromisoformat(last)).total_seconds() / 3600
        return elapsed_hours >= self._news_min_interval_hours

    async def _mark_fetched(self, symbol: str) -> None:
        if self._cache is None:
            return
        ttl = int(self._news_min_interval_hours * 3600) + _THROTTLE_KEY_TTL_SLACK_SECONDS
        await self._cache.set(f"news_fetch:{symbol}", datetime.now(UTC).isoformat(), ttl_seconds=ttl)

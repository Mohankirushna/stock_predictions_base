"""Agent 1 — Data Collection.

Pulls prices, company profiles, and news from the configured
MarketDataSource and persists them (companies, historical_prices, news —
the tables this schema provides for raw market data). Fundamentals,
analyst ratings, and insider trades are fetched too, but this schema has no
dedicated raw-data tables for them: fundamentals are computed and persisted
as structured ratios by the Fundamental Analysis Agent (M8), and analyst/
insider signals feed the Recommendation Agent's institutional score (M14)
at scoring time. Rather than let that data sit idle, this agent returns it
in the run summary for the same pipeline invocation to pass along.
"""
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.application.agents.base import AgentBase
from app.domain.intelligence.news import NewsArticle
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.ports.cache import Cache
from app.domain.ports.market_data_source import MarketDataSource
from app.domain.ports.unit_of_work import UnitOfWork


class DataCollectionAgent(AgentBase):
    name = "data_collection"

    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], market_data: MarketDataSource, cache: Cache | None = None
    ) -> None:
        super().__init__()
        self._uow_factory = uow_factory
        self._market_data = market_data
        self._cache = cache  # optional: publishes "prices" ticks for the WS layer (M17)

    async def _execute(
        self, symbols: list[str], *, history_days: int = 5, news_limit: int = 20
    ) -> dict[str, Any]:
        if not symbols:
            return {"companies_synced": 0, "symbols_skipped": [], "price_bars_inserted": 0, "news_articles_inserted": 0}

        end = date.today()
        start = end - timedelta(days=history_days)

        async with self._uow_factory() as uow:
            company_by_symbol = await self._upsert_companies(uow, symbols)
            price_bars = await self._collect_prices(uow, company_by_symbol, start, end)
            news_articles = await self._collect_news(uow, symbols, company_by_symbol, news_limit)
            await uow.commit()

        supplementary = await self._collect_supplementary(symbols)

        return {
            "companies_synced": len(company_by_symbol),
            "symbols_skipped": [s for s in symbols if s not in company_by_symbol],
            "price_bars_inserted": price_bars,
            "news_articles_inserted": news_articles,
            "supplementary": supplementary,
        }

    async def _upsert_companies(self, uow: UnitOfWork, symbols: list[str]) -> dict[str, Company]:
        result: dict[str, Company] = {}
        now = datetime.now(UTC)
        for symbol in symbols:
            existing = await uow.companies.get_by_symbol(symbol)
            info = await self._market_data.get_company_info(symbol)

            if existing is not None:
                if info is not None:
                    existing.name, existing.exchange = info.name, info.exchange
                    existing.sector, existing.industry = info.sector, info.industry
                    existing.country, existing.currency = info.country, info.currency
                    existing.market_cap = info.market_cap
                existing.mark_synced(now)
                await uow.companies.update(existing)
                result[symbol] = existing
            elif info is not None:
                company = Company(
                    symbol=symbol, name=info.name, exchange=info.exchange, sector=info.sector,
                    industry=info.industry, country=info.country, currency=info.currency,
                    market_cap=info.market_cap, last_synced_at=now,
                )
                await uow.companies.add(company)
                result[symbol] = company
            # else: vendor has no profile for this symbol — skip; reported via symbols_skipped
        return result

    async def _collect_prices(
        self, uow: UnitOfWork, company_by_symbol: dict[str, Company], start: date, end: date
    ) -> int:
        total = 0
        for symbol, company in company_by_symbol.items():
            bars = await self._bars_for(symbol, company, start, end)
            total += await uow.prices.add_bars(bars)
            if bars and self._cache is not None:
                latest = bars[-1]
                await self._cache.publish(
                    "prices",
                    {"symbol": symbol, "price": str(latest.close), "ts": latest.ts.isoformat()},
                )
        return total

    async def _bars_for(
        self, symbol: str, company: Company, start: date, end: date
    ) -> list[PriceBar]:
        """Historical candles first (works on vendor plans that support it);
        falls back to a single genuine bar built from today's real quote
        O/H/L/C when that endpoint isn't available (e.g. Finnhub's free
        tier, which 403s on /stock/candle but still serves real /quote
        data). One real day accumulates per run — no synthetic backfill."""
        try:
            raw_bars = await self._market_data.get_history(symbol, PriceInterval.D1, start, end)
            if raw_bars:
                return [
                    PriceBar(
                        company_id=company.id, ts=b.ts, interval=b.interval,
                        open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume,
                    )
                    for b in raw_bars
                ]
        except Exception:  # noqa: BLE001 — fall through to the quote-based bar below
            pass

        quotes = await self._market_data.get_quotes([symbol])
        if not quotes or quotes[0].open is None or quotes[0].high is None or quotes[0].low is None:
            return []
        quote = quotes[0]
        today = datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC)
        return [
            PriceBar(
                company_id=company.id, ts=today, interval=PriceInterval.D1,
                open=quote.open, high=quote.high, low=quote.low, close=quote.price,
                volume=quote.volume,
            )
        ]

    async def _collect_news(
        self, uow: UnitOfWork, symbols: list[str], company_by_symbol: dict[str, Company], limit: int
    ) -> int:
        inserted = 0
        now = datetime.now(UTC)
        seen_urls: set[str] = set()
        name_by_symbol = {symbol: company.name for symbol, company in company_by_symbol.items()}
        for item in await self._market_data.get_news(symbols, limit, name_by_symbol=name_by_symbol):
            # A single marketaux article commonly mentions several tracked
            # symbols (general market news), so per-symbol queries can surface
            # the same URL twice in one run, before either insert is flushed —
            # the DB-backed exists_by_url check alone can't catch that.
            if not item.url or item.url in seen_urls or await uow.news.exists_by_url(item.url):
                continue
            seen_urls.add(item.url)
            primary_symbol = item.symbols[0] if item.symbols else None
            company = company_by_symbol.get(primary_symbol) if primary_symbol else None
            article = NewsArticle(
                source=item.source, url=item.url, title=item.title, content=item.content,
                published_at=item.published_at, collected_at=now,
                company_id=company.id if company else None,
                extra_symbols=list(item.symbols[1:]),
            )
            await uow.news.add(article)
            inserted += 1
        return inserted

    async def _collect_supplementary(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        supplementary: dict[str, dict[str, Any]] = {}
        for symbol in symbols:
            supplementary[symbol] = {
                "fundamentals_raw": await self._market_data.get_fundamentals_raw(symbol),
                "analyst_ratings": await self._market_data.get_analyst_ratings(symbol),
                "insider_trades": await self._market_data.get_insider_trades(symbol),
            }
        return supplementary

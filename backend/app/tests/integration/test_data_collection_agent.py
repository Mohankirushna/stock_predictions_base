"""Data Collection Agent (Agent 1) against a live Postgres, with a fake
MarketDataSource so the test is deterministic and needs no vendor API key.
Skipped automatically when the database is unreachable."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.data_collection.agent import DataCollectionAgent
from app.core.config import get_settings
from app.domain.market.price import PriceInterval
from app.domain.ports.market_data_source import CompanyInfo, Quote, RawNewsItem, RawPriceBar
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


class FakeMarketDataSource:
    """Canned, deterministic responses — one company, two price bars, one
    news article, plus placeholder fundamentals/ratings/insider data."""

    name = "fake"

    def __init__(self, symbol: str, news_url: str) -> None:
        self._symbol = symbol
        self._news_url = news_url
        # Fixed, not datetime.now() — two agent runs must request identical
        # bar timestamps for the idempotency (duplicate-insert) test to hold.
        self._anchor = datetime(2024, 1, 2, tzinfo=UTC)

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        return [Quote(symbol=self._symbol, price=Decimal("100"), change_pct=Decimal("1"),
                       volume=Decimal("1000"), ts=self._anchor)]

    async def get_history(self, symbol, interval, start, end) -> list[RawPriceBar]:
        if symbol != self._symbol:
            return []
        return [
            RawPriceBar(symbol=symbol, ts=self._anchor - timedelta(days=1), interval=interval,
                        open=Decimal("100"), high=Decimal("105"), low=Decimal("99"),
                        close=Decimal("104"), volume=Decimal("1000")),
            RawPriceBar(symbol=symbol, ts=self._anchor, interval=interval,
                        open=Decimal("104"), high=Decimal("108"), low=Decimal("103"),
                        close=Decimal("107"), volume=Decimal("1200")),
        ]

    async def get_company_info(self, symbol: str) -> CompanyInfo | None:
        if symbol != self._symbol:
            return None
        return CompanyInfo(symbol=symbol, name="Fake Corp", exchange="NASDAQ", sector="Technology",
                            industry="Software", country="US", currency="USD",
                            market_cap=Decimal("500000000"))

    async def get_news(self, symbols: list[str], limit: int = 50) -> list[RawNewsItem]:
        return [
            RawNewsItem(source="Wire", url=self._news_url, title="Fake Corp beats estimates",
                        content="...", published_at=datetime.now(UTC), symbols=(self._symbol,)),
        ]

    async def get_fundamentals_raw(self, symbol: str) -> dict:
        return {"peNormalizedAnnual": 25.0}

    async def get_analyst_ratings(self, symbol: str) -> list[dict]:
        return [{"buy": 10, "hold": 2, "sell": 0}]

    async def get_insider_trades(self, symbol: str) -> list[dict]:
        return [{"name": "Founder", "change": 500}]


@pytest.fixture
async def uow_factory():
    engine = build_engine(get_settings())
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("postgres not reachable — run: docker compose up -d postgres")
    factory = build_session_factory(engine)
    yield lambda: SqlAlchemyUnitOfWork(factory)
    await engine.dispose()


async def test_collects_and_persists_company_prices_and_news(uow_factory) -> None:
    symbol = f"D{uuid4().hex[:6].upper()}"
    news_url = f"https://example.com/{uuid4().hex}"
    agent = DataCollectionAgent(uow_factory, FakeMarketDataSource(symbol, news_url))

    result = await agent.run(symbols=[symbol], history_days=5, news_limit=10)

    assert result.success is True
    assert result.summary["companies_synced"] == 1
    assert result.summary["symbols_skipped"] == []
    assert result.summary["price_bars_inserted"] == 2
    assert result.summary["news_articles_inserted"] == 1
    assert result.summary["supplementary"][symbol]["fundamentals_raw"] == {"peNormalizedAnnual": 25.0}

    async with uow_factory() as uow:
        company = await uow.companies.get_by_symbol(symbol)
        assert company is not None and company.name == "Fake Corp"
        latest = await uow.prices.latest_bar(company.id, PriceInterval.D1)
        assert latest is not None and latest.close == Decimal("107.000000")
        articles, total = await uow.news.for_company(company.id, page=1, size=10)
        assert total == 1
        assert articles[0].url == news_url


async def test_second_run_is_idempotent(uow_factory) -> None:
    symbol = f"D{uuid4().hex[:6].upper()}"
    news_url = f"https://example.com/{uuid4().hex}"
    source = FakeMarketDataSource(symbol, news_url)
    agent = DataCollectionAgent(uow_factory, source)

    first = await agent.run(symbols=[symbol])
    second = await agent.run(symbols=[symbol])

    assert first.summary["price_bars_inserted"] == 2
    assert second.summary["price_bars_inserted"] == 0  # duplicate bars no-op
    assert first.summary["news_articles_inserted"] == 1
    assert second.summary["news_articles_inserted"] == 0  # already exists by url
    assert second.summary["companies_synced"] == 1  # still updates the existing row


async def test_unknown_symbol_is_skipped_not_failed(uow_factory) -> None:
    agent = DataCollectionAgent(uow_factory, FakeMarketDataSource("REAL", "https://example.com/x"))
    result = await agent.run(symbols=["UNKNOWN_SYMBOL"])
    assert result.success is True
    assert result.summary["symbols_skipped"] == ["UNKNOWN_SYMBOL"]
    assert result.summary["companies_synced"] == 0


async def test_empty_symbol_list_short_circuits(uow_factory) -> None:
    agent = DataCollectionAgent(uow_factory, FakeMarketDataSource("X", "https://example.com/x"))
    result = await agent.run(symbols=[])
    assert result.success is True
    assert result.summary["companies_synced"] == 0

"""Tests the real Celery task business logic (the `_async` implementations)
against a live Postgres, with a fake MarketDataSource swapped into the
container so no vendor API key is needed. Skipped automatically when the
database is unreachable.

Doesn't touch Celery's broker/worker machinery at all — `@celery_app.task`
is just an asyncio.run() bridge around these same functions (see
data_tasks.py / analysis_tasks.py), so this is the real coverage.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.application.agents.news_intelligence.schema import NewsAnalysisOutput
from app.core.config import Settings
from app.core.container import container, wire
from app.domain.intelligence.news import NewsArticle
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.ports.ai_provider import AIProvider
from app.domain.ports.market_data_source import (
    CompanyInfo,
    MarketDataSource,
    Quote,
    RawNewsItem,
    RawPriceBar,
)
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.vector_store import VectorStore


class FakeMarketDataSource:
    name = "fake"

    def __init__(self, symbol: str) -> None:
        self._symbol = symbol

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        return []

    async def get_history(self, symbol, interval, start, end) -> list[RawPriceBar]:
        return []

    async def get_company_info(self, symbol: str) -> CompanyInfo | None:
        return None

    async def get_news(self, symbols: list[str], limit: int = 50) -> list[RawNewsItem]:
        return []

    async def get_fundamentals_raw(self, symbol: str) -> dict:
        return {"peTTM": 20.0} if symbol == self._symbol else {}

    async def get_analyst_ratings(self, symbol: str) -> list[dict]:
        return []

    async def get_insider_trades(self, symbol: str) -> list[dict]:
        return []


class FakeAIProvider:
    name = "fake"

    async def chat(self, request):
        raise NotImplementedError

    async def chat_structured(self, request, schema):
        from app.domain.ports.ai_provider import ChatResponse, ChatUsage

        output = NewsAnalysisOutput(sentiment=0.2, importance=4, summary="Routine update.")
        return output, ChatResponse(content="{}", provider=self.name, model="fake-1", usage=ChatUsage())

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class FakeVectorStore:
    async def upsert(self, collection, ids, vectors, payloads) -> None:
        pass

    async def search(self, collection, vector, limit=10, filters=None):
        return []


@pytest.fixture
async def wired():
    wire(Settings(app_secret_key="x" * 32, market={"finnhub_api_key": "unused"}))
    try:
        engine = container.resolve(AsyncEngine)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("postgres not reachable — run: docker compose up -d postgres")
    return container


async def test_compute_fundamentals_task_persists_snapshot(wired) -> None:
    from app.infrastructure.tasks.analysis_tasks import compute_fundamentals_async

    symbol = f"J{uuid4().hex[:6].upper()}"
    wired.register(MarketDataSource, lambda _: FakeMarketDataSource(symbol))

    async with wired.resolve(UnitOfWork) as uow:
        company = Company(symbol=symbol, name="Task Runner Co")
        await uow.companies.add(company)
        await uow.commit()
        company_id = company.id

    result = await compute_fundamentals_async(symbols=[symbol])
    assert result["success"] is True
    assert result["summary"] == {"computed": 1, "skipped": []}

    async with wired.resolve(UnitOfWork) as uow:
        snapshot = await uow.fundamentals.latest(company_id)
        assert snapshot is not None and snapshot.pe == Decimal("20.0")


async def test_compute_technicals_task_persists_snapshot(wired) -> None:
    from app.infrastructure.tasks.analysis_tasks import compute_technicals_async

    symbol = f"J{uuid4().hex[:6].upper()}"
    wired.register(MarketDataSource, lambda _: FakeMarketDataSource(symbol))

    async with wired.resolve(UnitOfWork) as uow:
        company = Company(symbol=symbol, name="Task Runner TA Co")
        await uow.companies.add(company)
        now = datetime.now(UTC)
        bars = [
            PriceBar(
                company_id=company.id, ts=now - timedelta(days=i), interval=PriceInterval.D1,
                open=Decimal("100"), high=Decimal("101"), low=Decimal("99"), close=Decimal("100"),
                volume=Decimal("1000"),
            )
            for i in range(25, 0, -1)
        ]
        await uow.prices.add_bars(bars)
        await uow.commit()
        company_id = company.id

    result = await compute_technicals_async(symbols=[symbol])
    assert result["success"] is True
    assert result["summary"] == {"computed": 1, "skipped": []}

    async with wired.resolve(UnitOfWork) as uow:
        snapshot = await uow.technicals.latest(company_id, PriceInterval.D1)
        assert snapshot is not None


async def test_collect_market_data_task_reports_skip_for_unknown_symbol(wired) -> None:
    from app.infrastructure.tasks.data_tasks import collect_market_data_async

    wired.register(MarketDataSource, lambda _: FakeMarketDataSource("NOPE"))
    result = await collect_market_data_async(symbols=["UNKNOWN_SYMBOL_XYZ"])
    assert result["success"] is True
    assert result["summary"]["symbols_skipped"] == ["UNKNOWN_SYMBOL_XYZ"]


async def test_symbols_none_resolves_via_target_symbols_helper(wired) -> None:
    from app.infrastructure.tasks.analysis_tasks import compute_fundamentals_async

    symbol = f"J{uuid4().hex[:6].upper()}"
    wired.register(MarketDataSource, lambda _: FakeMarketDataSource(symbol))

    async with wired.resolve(UnitOfWork) as uow:
        await uow.companies.add(Company(symbol=symbol, name="Auto Resolve Co"))
        await uow.commit()

    # symbols=None -> the task resolves targets itself via list_active_symbols();
    # other tests' companies may also be present, so just confirm ours ran.
    result = await compute_fundamentals_async(symbols=None)
    assert result["success"] is True
    assert symbol not in result["summary"]["skipped"]


async def test_analyze_news_task_processes_unanalyzed_article(wired) -> None:
    from app.infrastructure.tasks.ai_tasks import analyze_news_async

    wired.register(AIProvider, lambda _: FakeAIProvider())
    wired.register(VectorStore, lambda _: FakeVectorStore())

    symbol = f"J{uuid4().hex[:6].upper()}"
    url = f"https://example.com/{uuid4().hex}"
    async with wired.resolve(UnitOfWork) as uow:
        company = Company(symbol=symbol, name="Task Runner News Co")
        await uow.companies.add(company)
        await uow.commit()

    async with wired.resolve(UnitOfWork) as uow:
        await uow.news.add(
            NewsArticle(source="Wire", url=url, title="Task runner test article", company_id=company.id)
        )
        await uow.commit()

    result = await analyze_news_async(limit=50)
    assert result["success"] is True

    async with wired.resolve(UnitOfWork) as uow:
        articles, _ = await uow.news.for_company(company.id, page=1, size=10)
        stored = next(a for a in articles if a.url == url)
        assert stored.is_analyzed
        assert stored.analysis.summary == "Routine update."

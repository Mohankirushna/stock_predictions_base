"""News Intelligence Agent (Agent 2) against a live Postgres, with fake
AIProvider and VectorStore doubles so the test is deterministic and needs
no vendor API key. Skipped automatically when the database is unreachable.
"""
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.news_intelligence.agent import NewsIntelligenceAgent
from app.application.agents.news_intelligence.schema import NewsAnalysisOutput
from app.core.config import get_settings
from app.domain.intelligence.news import NewsArticle
from app.domain.market.company import Company
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatUsage
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


class FakeAIProvider:
    """Stands in for the whole AIProvider port (router + adapter + JSON
    parsing already covered by M5's tests) — hands back canned structured
    output per request via a caller-supplied respond() callback."""

    name = "fake"

    def __init__(self, respond: Callable[[ChatRequest], NewsAnalysisOutput]) -> None:
        self._respond = respond

    async def chat(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError

    async def chat_structured(self, request: ChatRequest, schema: type) -> tuple[Any, ChatResponse]:
        output = self._respond(request)
        response = ChatResponse(
            content="{}", provider=self.name, model="fake-1",
            usage=ChatUsage(tokens_in=42, tokens_out=17, cost_usd=0.002, latency_ms=5),
        )
        return output, response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserts: list[tuple] = []

    async def upsert(self, collection, ids, vectors, payloads) -> None:
        self.upserts.append((collection, ids, vectors, payloads))

    async def search(self, collection, vector, limit=10, filters=None):
        return []


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


async def _seed_company_and_article(uow_factory, *, title: str = "Earnings beat expectations"):
    symbol = f"N{uuid4().hex[:6].upper()}"
    url = f"https://example.com/{uuid4().hex}"
    company = Company(symbol=symbol, name="News Co")
    # Two transactions, not one: SQLAlchemy's flush doesn't reliably order
    # inserts across two ORM classes with no explicit relationship() between
    # them, even though the FK exists at the Table/Column level. The Data
    # Collection Agent (M6) sidesteps this the same way — companies are
    # committed before news in a separate transaction.
    async with uow_factory() as uow:
        await uow.companies.add(company)
        await uow.commit()

    async with uow_factory() as uow:
        article = NewsArticle(
            source="Wire", url=url, title=title, content=f"{title}. Full article body here.",
            published_at=datetime.now(UTC), collected_at=datetime.now(UTC),
            company_id=company.id,
        )
        await uow.news.add(article)
        await uow.commit()
        return company, article


async def test_analyzes_article_and_embeds_it(uow_factory) -> None:
    company, article = await _seed_company_and_article(uow_factory)

    def respond(request: ChatRequest) -> NewsAnalysisOutput:
        return NewsAnalysisOutput(
            sentiment=0.7, importance=8, summary="Company beat earnings expectations.",
            risks=["margin pressure"], opportunities=["expansion"], industry="Technology",
            expected_impact="Likely positive short-term move", mentioned_symbols=[company.symbol],
        )

    vector_store = FakeVectorStore()
    agent = NewsIntelligenceAgent(uow_factory, FakeAIProvider(respond), vector_store)
    result = await agent.run(limit=50)

    assert result.success is True
    assert article.url not in [f["url"] for f in result.summary["failed"]]

    async with uow_factory() as uow:
        articles, _ = await uow.news.for_company(company.id, page=1, size=10)
        stored = next(a for a in articles if a.url == article.url)
        assert stored.is_analyzed
        assert stored.analysis.sentiment == 0.7
        assert stored.analysis.importance == 8
        assert stored.analysis.summary == "Company beat earnings expectations."
        assert stored.embedding_id == str(stored.id)

    # Other unanalyzed articles from earlier test runs may share this batch
    # (get_unanalyzed scans the whole table) — find our specific upsert call.
    matching = [u for u in vector_store.upserts if u[1] == [str(stored.id)]]
    assert len(matching) == 1
    collection, ids, _vectors, payloads = matching[0]
    assert collection == "news_embeddings"
    assert payloads[0]["symbol"] == company.symbol


async def test_one_failing_article_does_not_sink_the_batch(uow_factory) -> None:
    _, good_article = await _seed_company_and_article(uow_factory, title="Good article")
    _, bad_article = await _seed_company_and_article(uow_factory, title="FAIL_ME article")

    def respond(request: ChatRequest) -> NewsAnalysisOutput:
        if "FAIL_ME" in request.messages[-1].content:
            raise RuntimeError("simulated AI failure")
        return NewsAnalysisOutput(sentiment=0.1, importance=3, summary="Routine update.")

    agent = NewsIntelligenceAgent(uow_factory, FakeAIProvider(respond), FakeVectorStore())
    result = await agent.run(limit=50)

    assert result.success is True
    failed_urls = [f["url"] for f in result.summary["failed"]]
    assert bad_article.url in failed_urls
    assert good_article.url not in failed_urls

    async with uow_factory() as uow:
        bad_articles, _ = await uow.news.for_company(bad_article.company_id, page=1, size=10)
        stored_bad = next(a for a in bad_articles if a.url == bad_article.url)
        assert not stored_bad.is_analyzed  # failed article left untouched, not partially written


async def test_embedding_failure_does_not_undo_the_analysis(uow_factory) -> None:
    company, article = await _seed_company_and_article(uow_factory)

    class BrokenVectorStore(FakeVectorStore):
        async def upsert(self, collection, ids, vectors, payloads) -> None:
            raise RuntimeError("qdrant is down")

    def respond(request: ChatRequest) -> NewsAnalysisOutput:
        return NewsAnalysisOutput(sentiment=-0.2, importance=4, summary="Minor negative update.")

    agent = NewsIntelligenceAgent(uow_factory, FakeAIProvider(respond), BrokenVectorStore())
    result = await agent.run(limit=50)

    assert result.success is True
    assert result.summary["failed"] == []  # embedding failure is swallowed, not counted as an article failure

    async with uow_factory() as uow:
        articles, _ = await uow.news.for_company(company.id, page=1, size=10)
        stored = next(a for a in articles if a.url == article.url)
        assert stored.is_analyzed
        assert stored.analysis.sentiment == -0.2
        assert stored.embedding_id is None  # embedding never succeeded

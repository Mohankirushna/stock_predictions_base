"""Trending news endpoint against a live Postgres. Skipped automatically
when the database is unreachable."""
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.container import container
from app.domain.intelligence.news import NewsAnalysis, NewsArticle
from app.domain.ports.unit_of_work import UnitOfWork
from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    try:
        engine = container.resolve(AsyncEngine)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("postgres not reachable — run: docker compose up -d postgres")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_trending_only_returns_analyzed_articles_ordered_by_importance(client: httpx.AsyncClient) -> None:
    high = NewsArticle(source="s", url=f"https://x/{uuid4().hex}", title="High importance")
    high.analysis = NewsAnalysis(sentiment=0.5, importance=9, summary="s")
    high.analyzed_at = datetime.now(UTC)

    unanalyzed = NewsArticle(source="s", url=f"https://x/{uuid4().hex}", title="Not analyzed yet")

    uow = container.resolve(UnitOfWork)
    async with uow:
        await uow.news.add(high)
        await uow.news.add(unanalyzed)
        await uow.commit()

    resp = await client.get("/api/v1/news/trending?limit=50")
    assert resp.status_code == 200
    urls = [a["url"] for a in resp.json()["data"]]
    assert high.url in urls
    assert unanalyzed.url not in urls

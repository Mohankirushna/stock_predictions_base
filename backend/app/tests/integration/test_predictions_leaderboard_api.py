"""Prediction leaderboard endpoint against a live Postgres. Skipped
automatically when the database is unreachable."""
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.container import container
from app.domain.learning.evaluation import LearningRecord, LearningScope
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


async def test_leaderboard_returns_sorted_entries(client: httpx.AsyncClient) -> None:
    sector = f"LBApi{uuid4().hex[:6]}"
    uow = container.resolve(UnitOfWork)
    async with uow:
        await uow.learning.save_record(
            LearningRecord(scope=LearningScope.SECTOR, key=sector, window="7d",
                            metric={"rolling_accuracy": 0.42, "sample_size": 5})
        )
        await uow.commit()

    resp = await client.get("/api/v1/predictions/leaderboard")
    assert resp.status_code == 200
    entries = resp.json()["data"]
    matching = [e for e in entries if e["sector"] == sector]
    assert matching == [{"sector": sector, "horizon": "7d", "rolling_accuracy": 0.42, "sample_size": 5}]

    # Sorted descending by accuracy overall.
    accuracies = [e["rolling_accuracy"] for e in entries]
    assert accuracies == sorted(accuracies, reverse=True)

"""Celery tasks for Agent 1 — Data Collection. Runs on the `data` queue.

The `_async` function is the real, directly-testable implementation; the
`@celery_app.task` wrapper bridges it onto the worker process's persistent
event loop (see loop.py — NOT a fresh asyncio.run() per task).
"""
from typing import Any

from app.application.agents.data_collection.agent import DataCollectionAgent
from app.core.container import container
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.loop import run
from app.infrastructure.tasks.runner import run_agent_task


async def collect_market_data_async(symbols: list[str] | None = None) -> dict[str, Any]:
    return await run_agent_task(container.resolve(DataCollectionAgent), symbols)


@celery_app.task(name="data.collect_market_data")
def collect_market_data(symbols: list[str] | None = None) -> dict[str, Any]:
    return run(collect_market_data_async(symbols))

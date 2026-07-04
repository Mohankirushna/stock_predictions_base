"""Celery tasks for Agent 3 (Technical) and Agent 4 (Fundamental) analysis.
Runs on the `analysis` queue. See loop.py for the persistent-event-loop
bridge rationale."""
from typing import Any

from app.application.agents.fundamental_analysis.agent import FundamentalAnalysisAgent
from app.application.agents.technical_analysis.agent import TechnicalAnalysisAgent
from app.core.container import container
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.loop import run
from app.infrastructure.tasks.runner import run_agent_task


async def compute_technicals_async(symbols: list[str] | None = None) -> dict[str, Any]:
    return await run_agent_task(container.resolve(TechnicalAnalysisAgent), symbols)


async def compute_fundamentals_async(symbols: list[str] | None = None) -> dict[str, Any]:
    return await run_agent_task(container.resolve(FundamentalAnalysisAgent), symbols)


@celery_app.task(name="analysis.compute_technicals")
def compute_technicals(symbols: list[str] | None = None) -> dict[str, Any]:
    return run(compute_technicals_async(symbols))


@celery_app.task(name="analysis.compute_fundamentals")
def compute_fundamentals(symbols: list[str] | None = None) -> dict[str, Any]:
    return run(compute_fundamentals_async(symbols))

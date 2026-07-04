"""Celery task for Agent 2 — News Intelligence. Runs on the `ai` queue.
See loop.py for the persistent-event-loop bridge rationale.

Unlike the data/analysis tasks, this one doesn't take a symbol list — it
just processes the next batch of unanalyzed articles regardless of company.
"""
from typing import Any

from app.application.agents.market_intelligence.agent import MarketIntelligenceAgent
from app.application.agents.news_intelligence.agent import NewsIntelligenceAgent
from app.application.agents.opportunity.agent import OpportunityDiscoveryAgent
from app.application.agents.recommendation.agent import RecommendationAgent
from app.application.agents.research.agent import ResearchAgent
from app.core.config import Settings
from app.core.container import container
from app.domain.ports.unit_of_work import UnitOfWork
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.loop import run
from app.infrastructure.tasks.symbols import target_symbols


def _shape(result) -> dict[str, Any]:
    return {"agent": result.agent, "success": result.success, "summary": result.summary, "error": result.error}


async def analyze_news_async(limit: int = 20) -> dict[str, Any]:
    return _shape(await container.resolve(NewsIntelligenceAgent).run(limit=limit))


async def market_intelligence_async() -> dict[str, Any]:
    return _shape(await container.resolve(MarketIntelligenceAgent).run())


@celery_app.task(name="ai.analyze_news")
def analyze_news(limit: int = 20) -> dict[str, Any]:
    return run(analyze_news_async(limit))


async def refresh_research_async(symbols: list[str] | None = None, force: bool = False) -> dict[str, Any]:
    if symbols is None:
        async with container.resolve(UnitOfWork) as uow:
            symbols = await target_symbols(uow, container.resolve(Settings))
    return _shape(await container.resolve(ResearchAgent).run(symbols=symbols, force=force))


@celery_app.task(name="ai.market_intelligence")
def market_intelligence() -> dict[str, Any]:
    return run(market_intelligence_async())


@celery_app.task(name="ai.refresh_research")
def refresh_research(symbols: list[str] | None = None, force: bool = False) -> dict[str, Any]:
    return run(refresh_research_async(symbols, force))


async def discover_opportunities_async() -> dict[str, Any]:
    return _shape(await container.resolve(OpportunityDiscoveryAgent).run())


@celery_app.task(name="ai.discover_opportunities")
def discover_opportunities() -> dict[str, Any]:
    return run(discover_opportunities_async())


async def generate_recommendations_async(symbols: list[str] | None = None) -> dict[str, Any]:
    if symbols is None:
        async with container.resolve(UnitOfWork) as uow:
            symbols = await target_symbols(uow, container.resolve(Settings))
    return _shape(await container.resolve(RecommendationAgent).run(symbols=symbols))


@celery_app.task(name="alerts.generate_recommendations")
def generate_recommendations(symbols: list[str] | None = None) -> dict[str, Any]:
    return run(generate_recommendations_async(symbols))


async def evaluate_alerts_async() -> dict[str, Any]:
    from app.application.agents.alert.agent import AlertAgent

    return _shape(await container.resolve(AlertAgent).run())


@celery_app.task(name="alerts.evaluate_alerts")
def evaluate_alerts() -> dict[str, Any]:
    return run(evaluate_alerts_async())


async def evaluate_predictions_async() -> dict[str, Any]:
    from app.application.agents.learning.agent import LearningAgent

    return _shape(await container.resolve(LearningAgent).run())


@celery_app.task(name="ai.evaluate_predictions")
def evaluate_predictions() -> dict[str, Any]:
    return run(evaluate_predictions_async())

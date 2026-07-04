"""Admin endpoints — every route requires the admin role (require_admin)."""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_uow, require_admin
from app.api.v1.envelope import ok
from app.api.v1.schemas.admin import (
    AdminSettingsOut,
    AdminStatsOut,
    AIUsageEntryOut,
    RunAgentAccepted,
    UpdateAdminSettingsRequest,
)
from app.application.scoring.engine import DEFAULT_WEIGHTS, WEIGHTS_CACHE_KEY
from app.core.config import Settings, get_settings
from app.core.container import container
from app.core.errors import NotFoundError
from app.domain.identity.user import User
from app.domain.ports.cache import Cache
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usage_recorder import UsageRecorder

router = APIRouter(prefix="/admin", tags=["admin"])

_AGENT_TASKS: dict[str, str] = {
    "data_collection": "app.infrastructure.tasks.data_tasks",
    "technical_analysis": "app.infrastructure.tasks.analysis_tasks",
    "fundamental_analysis": "app.infrastructure.tasks.analysis_tasks",
    "news_intelligence": "app.infrastructure.tasks.ai_tasks",
    "market_intelligence": "app.infrastructure.tasks.ai_tasks",
    "research": "app.infrastructure.tasks.ai_tasks",
    "opportunity_discovery": "app.infrastructure.tasks.ai_tasks",
    "recommendation": "app.infrastructure.tasks.ai_tasks",
    "alert": "app.infrastructure.tasks.ai_tasks",
    "learning": "app.infrastructure.tasks.ai_tasks",
}
_AGENT_TASK_FUNCS: dict[str, str] = {
    "data_collection": "collect_market_data",
    "technical_analysis": "compute_technicals",
    "fundamental_analysis": "compute_fundamentals",
    "news_intelligence": "analyze_news",
    "market_intelligence": "market_intelligence",
    "research": "refresh_research",
    "opportunity_discovery": "discover_opportunities",
    "recommendation": "generate_recommendations",
    "alert": "evaluate_alerts",
    "learning": "evaluate_predictions",
}


@router.get("/stats")
async def admin_stats(
    _admin: User = Depends(require_admin), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    usage = container.resolve(UsageRecorder)
    _, total_recs = await uow.recommendations.screen(min_score=0.0, sector=None, page=1, size=1)
    stats = AdminStatsOut(
        total_users=await uow.users.count_all(),
        active_alerts=await uow.alerts.count_active(),
        total_recommendations=total_recs,
        ai_spend_usd=await usage.total_cost(provider=None, since=None),
    )
    return ok(stats)


@router.get("/ai-usage")
async def ai_usage_log(
    provider: str | None = None, since: datetime | None = Query(None, alias="from"),
    limit: int = Query(100, ge=1, le=1000), _admin: User = Depends(require_admin),
) -> dict[str, Any]:
    usage = container.resolve(UsageRecorder)
    entries = await usage.list_recent(provider, since, limit)
    return ok([AIUsageEntryOut(**vars(e)) for e in entries])


@router.post("/agents/{name}/run", status_code=202)
async def run_agent(name: str, _admin: User = Depends(require_admin)) -> dict[str, Any]:
    import importlib

    if name not in _AGENT_TASK_FUNCS:
        raise NotFoundError(f"unknown agent {name!r}; valid names: {sorted(_AGENT_TASK_FUNCS)}")

    module = importlib.import_module(_AGENT_TASKS[name])
    task = getattr(module, _AGENT_TASK_FUNCS[name])
    result = task.delay()
    return ok(RunAgentAccepted(task_id=result.id, agent=name).model_dump())


@router.get("/settings")
async def get_admin_settings(
    _admin: User = Depends(require_admin), settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    cache = container.resolve(Cache)
    weights = await cache.get(WEIGHTS_CACHE_KEY) or DEFAULT_WEIGHTS
    return ok(
        AdminSettingsOut(
            ai_provider=settings.ai.provider, ai_fallback_providers=settings.ai.fallback_providers,
            score_weights=weights,
        )
    )


@router.patch("/settings")
async def update_admin_settings(
    body: UpdateAdminSettingsRequest, _admin: User = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    cache = container.resolve(Cache)
    if body.score_weights is not None:
        await cache.set(WEIGHTS_CACHE_KEY, body.score_weights, ttl_seconds=86400 * 365)  # effectively persistent

    weights = await cache.get(WEIGHTS_CACHE_KEY) or DEFAULT_WEIGHTS
    return ok(
        AdminSettingsOut(
            ai_provider=settings.ai.provider, ai_fallback_providers=settings.ai.fallback_providers,
            score_weights=weights,
        )
    )

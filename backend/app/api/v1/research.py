"""Research/recommendation read endpoints and async report generation.
Report generation is enqueued on Celery and polled via task id — the agent
call itself can take many seconds, too slow for a synchronous request."""
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import get_uow
from app.api.v1.envelope import ok, paginated
from app.api.v1.schemas.companies import RecommendationOut
from app.api.v1.schemas.research import GenerateReportAccepted, OpportunityOut, TaskStatusOut
from app.core.container import container
from app.core.errors import NotFoundError
from app.domain.ports.cache import Cache
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.research.opportunity import CACHE_KEY

router = APIRouter(tags=["research"])


@router.get("/research/opportunities")
async def list_opportunities() -> dict[str, Any]:
    cache = container.resolve(Cache)
    cached = await cache.get(CACHE_KEY) or []
    return ok(
        [
            OpportunityOut(
                symbol=o["symbol"], company_name=o["company_name"], reasons=o["reasons"],
                confidence=o["confidence"], catalysts=o["catalysts"], risk=o["risk"],
                entry_zone_low=Decimal(o["entry_zone_low"]), entry_zone_high=Decimal(o["entry_zone_high"]),
            )
            for o in cached
        ]
    )


@router.post("/research/reports/{symbol}/generate", status_code=202)
async def generate_report(symbol: str, uow: UnitOfWork = Depends(get_uow)) -> JSONResponse:
    from app.infrastructure.tasks.ai_tasks import refresh_research

    company = await uow.companies.get_by_symbol(symbol.upper())
    if company is None:
        raise NotFoundError(f"no company found for symbol {symbol.upper()!r}")

    task = refresh_research.delay(symbols=[company.symbol], force=True)
    accepted = GenerateReportAccepted(task_id=task.id, symbol=company.symbol)
    return JSONResponse(status_code=202, content=ok(accepted.model_dump()))


@router.get("/research/tasks/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    from app.infrastructure.tasks.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    payload = result.result if result.ready() and not result.failed() else None
    status = TaskStatusOut(
        task_id=task_id, status=result.status, result=payload if isinstance(payload, dict) else None
    )
    return ok(status.model_dump())


@router.get("/recommendations")
async def screen_recommendations(
    min_score: float = Query(0.0, ge=0.0, le=100.0), sector: str | None = None,
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    recs, total = await uow.recommendations.screen(min_score, sector, page, size)
    out = []
    for r in recs:
        company = await uow.companies.get(r.company_id)
        out.append(RecommendationOut.from_domain(r, company.symbol if company else "?"))
    return paginated(out, page, size, total)

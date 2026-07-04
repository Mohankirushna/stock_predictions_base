"""Cross-company news endpoint — backs the dashboard's trending news feed.
Per-company news lives under /companies/{symbol}/news (M15); this is the
one place that reads across all companies."""
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_uow
from app.api.v1.envelope import ok
from app.api.v1.schemas.companies import NewsOut
from app.domain.ports.unit_of_work import UnitOfWork

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/trending")
async def trending_news(
    limit: int = Query(20, ge=1, le=100), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    articles = await uow.news.trending(limit)
    return ok([NewsOut.from_domain(a) for a in articles])

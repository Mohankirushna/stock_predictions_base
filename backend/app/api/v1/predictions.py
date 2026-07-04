"""Prediction accuracy leaderboard — reads the Learning Agent's rolling
per-sector, per-horizon accuracy records (M18). Public, no auth: this is
the transparency feature that lets users judge the platform's track record."""
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_uow
from app.api.v1.envelope import ok
from app.api.v1.schemas.predictions import LeaderboardEntryOut
from app.domain.learning.evaluation import LearningScope
from app.domain.ports.unit_of_work import UnitOfWork

router = APIRouter(tags=["predictions"])


@router.get("/predictions/leaderboard")
async def prediction_leaderboard(uow: UnitOfWork = Depends(get_uow)) -> dict[str, Any]:
    records = await uow.learning.list_by_scope(LearningScope.SECTOR.value)
    entries = [
        LeaderboardEntryOut(
            sector=r.key, horizon=r.window,
            rolling_accuracy=r.metric.get("rolling_accuracy", 0.0), sample_size=r.metric.get("sample_size", 0),
        )
        for r in records
    ]
    entries.sort(key=lambda e: e.rolling_accuracy, reverse=True)
    return ok(entries)

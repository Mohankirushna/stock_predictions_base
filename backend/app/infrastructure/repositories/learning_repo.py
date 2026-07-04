from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.learning.evaluation import LearningRecord, LearningScope, PredictionEvaluation
from app.infrastructure.db.models.learning import LearningDataModel, PredictionHistoryModel
from app.infrastructure.db.models.research import PredictionModel


class SqlLearningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_evaluation(self, e: PredictionEvaluation) -> None:
        self._session.add(
            PredictionHistoryModel(
                id=e.id, prediction_id=e.prediction_id, horizon=e.horizon.value,
                evaluated_at=e.evaluated_at, actual_price=e.actual_price,
                direction_correct=e.direction_correct, hit_stop_loss=e.hit_stop_loss,
                hit_tp1=e.hit_tp1, hit_tp2=e.hit_tp2, hit_tp3=e.hit_tp3,
                max_drawdown_pct=e.max_drawdown_pct, max_gain_pct=e.max_gain_pct,
                accuracy_score=e.accuracy_score,
            )
        )
        # Stamp the prediction so due_for_evaluation stops returning it.
        await self._session.execute(
            update(PredictionModel)
            .where(PredictionModel.id == e.prediction_id)
            .values(evaluated_at=datetime.now(UTC))
        )

    async def save_record(self, record: LearningRecord) -> None:
        values = {
            "scope": record.scope.value, "key": record.key,
            "window": record.window, "metric": record.metric,
        }
        stmt = pg_insert(LearningDataModel).values(id=record.id, **values)
        stmt = stmt.on_conflict_do_update(constraint="uq_learning_scope", set_=values)
        await self._session.execute(stmt)

    async def get_record(self, scope: str, key: str, window: str) -> LearningRecord | None:
        m = await self._session.scalar(
            select(LearningDataModel).where(
                LearningDataModel.scope == scope,
                LearningDataModel.key == key,
                LearningDataModel.window == window,
            )
        )
        if m is None:
            return None
        return self._to_domain(m)

    async def list_by_scope(self, scope: str) -> list[LearningRecord]:
        rows = await self._session.scalars(
            select(LearningDataModel)
            .where(LearningDataModel.scope == scope)
            .order_by(LearningDataModel.key, LearningDataModel.window)
        )
        return [self._to_domain(m) for m in rows]

    @staticmethod
    def _to_domain(m: LearningDataModel) -> LearningRecord:
        return LearningRecord(
            id=m.id, created_at=m.created_at, updated_at=m.updated_at,
            scope=LearningScope(m.scope), key=m.key, window=m.window,
            metric=dict(m.metric or {}),
        )

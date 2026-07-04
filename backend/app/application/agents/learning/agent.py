"""Agent 11 — Learning. Evaluates predictions once their horizon (1d/7d/
30d/90d) has elapsed: accuracy, stop/target hits, max drawdown/gain — then
folds the result into a rolling per-sector, per-horizon accuracy record
that future scoring can read back (the "improve future scoring" feedback
loop). No AI: this is pure Python arithmetic over price history.
"""
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.application.agents.base import AgentBase
from app.application.agents.learning import analysis as an
from app.domain.learning.evaluation import LearningRecord, LearningScope, PredictionEvaluation
from app.domain.market.price import PriceInterval
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.research.prediction import Prediction

_BATCH_LIMIT = 50


class LearningAgent(AgentBase):
    name = "learning"

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        super().__init__()
        self._uow_factory = uow_factory

    async def _execute(self) -> dict[str, Any]:
        evaluated, skipped = 0, []
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            for prediction in await uow.predictions.due_for_evaluation(now, _BATCH_LIMIT):
                if await self._evaluate_one(uow, prediction, now):
                    evaluated += 1
                else:
                    skipped.append(str(prediction.id))
            await uow.commit()
        return {"evaluated": evaluated, "skipped": skipped}

    async def _evaluate_one(self, uow: UnitOfWork, prediction: Prediction, now: datetime) -> bool:
        recommendation = await uow.recommendations.get(prediction.recommendation_id)
        if recommendation is None:
            return False

        bars = await uow.prices.get_bars(prediction.company_id, PriceInterval.D1, prediction.predicted_at, now)
        if not bars:
            return False

        actual_price = bars[-1].close
        direction_correct = (
            an.determine_actual_direction(prediction.price_at_prediction, actual_price)
            == prediction.expected_direction
        )
        max_drawdown_pct, max_gain_pct = an.compute_drawdown_and_gain(bars, prediction.price_at_prediction)
        hits = an.compute_hit_flags(bars, recommendation)
        accuracy_score = an.compute_accuracy_score(direction_correct, hits)

        await uow.learning.add_evaluation(
            PredictionEvaluation(
                prediction_id=prediction.id, horizon=prediction.horizon, evaluated_at=now,
                actual_price=actual_price, direction_correct=direction_correct,
                hit_stop_loss=hits.hit_stop_loss, hit_tp1=hits.hit_tp1, hit_tp2=hits.hit_tp2,
                hit_tp3=hits.hit_tp3, max_drawdown_pct=max_drawdown_pct, max_gain_pct=max_gain_pct,
                accuracy_score=accuracy_score,
            )
        )

        company = await uow.companies.get(prediction.company_id)
        sector = (company.sector if company else "") or "Unknown"
        await self._update_rolling_record(uow, sector, prediction.horizon.value, accuracy_score)
        return True

    async def _update_rolling_record(self, uow: UnitOfWork, sector: str, window: str, score: float) -> None:
        existing = await uow.learning.get_record(LearningScope.SECTOR.value, sector, window)
        updated_metric = an.update_rolling_accuracy(existing.metric if existing else {}, score)
        await uow.learning.save_record(
            LearningRecord(scope=LearningScope.SECTOR, key=sector, window=window, metric=updated_metric)
        )

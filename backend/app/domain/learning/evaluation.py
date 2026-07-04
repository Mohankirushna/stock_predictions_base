"""Learning-loop domain objects: how a prediction actually played out, and the
aggregated records the Learning Agent uses to recalibrate scoring weights."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.common.entity import Entity
from app.domain.common.errors import InvariantViolation
from app.domain.research.prediction import Horizon


@dataclass(kw_only=True, eq=False)
class PredictionEvaluation(Entity):
    prediction_id: UUID
    horizon: Horizon
    evaluated_at: datetime
    actual_price: Decimal
    direction_correct: bool
    hit_stop_loss: bool = False
    hit_tp1: bool = False
    hit_tp2: bool = False
    hit_tp3: bool = False
    max_drawdown_pct: Decimal = Decimal("0")
    max_gain_pct: Decimal = Decimal("0")
    accuracy_score: float = 0.0  # 0.0–1.0 composite

    def __post_init__(self) -> None:
        if not 0.0 <= self.accuracy_score <= 1.0:
            raise InvariantViolation(f"accuracy_score out of range: {self.accuracy_score}")


class LearningScope(StrEnum):
    GLOBAL = "global"
    SECTOR = "sector"
    AGENT = "agent"
    PROVIDER = "provider"


@dataclass(kw_only=True, eq=False)
class LearningRecord(Entity):
    scope: LearningScope
    key: str  # e.g. sector name, agent name, provider name
    window: str  # e.g. "90d"
    metric: dict[str, Any] = field(default_factory=dict)
    # metric examples: {"rolling_accuracy": 0.61, "calibration": [...],
    #                   "weight_adjustments": {"technicals": +0.03}}

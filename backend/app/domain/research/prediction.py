from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.common.entity import Entity
from app.domain.common.errors import InvariantViolation
from app.domain.common.values import PriceRange


class Horizon(StrEnum):
    D1 = "1d"
    D7 = "7d"
    D30 = "30d"
    D90 = "90d"


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


@dataclass(kw_only=True, eq=False)
class Prediction(Entity):
    """A falsifiable claim derived from a recommendation. The Learning Agent
    evaluates it after each horizon elapses."""

    recommendation_id: UUID
    company_id: UUID
    predicted_at: datetime
    horizon: Horizon
    expected_direction: Direction
    expected_range: PriceRange
    confidence: float
    price_at_prediction: Decimal

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise InvariantViolation(f"confidence out of range: {self.confidence}")

    def due_at(self) -> datetime:
        from datetime import timedelta

        days = {Horizon.D1: 1, Horizon.D7: 7, Horizon.D30: 30, Horizon.D90: 90}[self.horizon]
        return self.predicted_at + timedelta(days=days)

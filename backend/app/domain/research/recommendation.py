"""Recommendation aggregate — research guidance, never a trade order.

Invariants enforce the product's core promise: every recommendation carries
an explanation, a non-empty uncertainty note, and a consistent price ladder.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.common.entity import AggregateRoot
from app.domain.common.errors import InvariantViolation
from app.domain.common.values import PriceRange


class Action(StrEnum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    REDUCE = "reduce"
    AVOID = "avoid"


class HoldingPeriod(StrEnum):
    SWING = "swing"  # days
    SHORT = "short"  # weeks
    MEDIUM = "medium"  # months
    LONG = "long"  # year+


class RecommendationStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class ScoreBreakdown:
    """Master-score components, each 0–100."""

    news: float
    technicals: float
    fundamentals: float
    momentum: float
    institutional: float
    risk: float  # higher = safer (already inverted)
    macro: float

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if not 0.0 <= value <= 100.0:
                raise InvariantViolation(f"score component {name} out of range: {value}")

    def as_dict(self) -> dict[str, float]:
        return dict(self.__dict__)


@dataclass(kw_only=True, eq=False)
class Recommendation(AggregateRoot):
    company_id: UUID
    action: Action
    current_price: Decimal
    entry_zone: PriceRange
    stop_loss: Decimal
    take_profit_1: Decimal
    take_profit_2: Decimal
    take_profit_3: Decimal
    holding_period: HoldingPeriod
    confidence: float  # 0.0–1.0
    risk_reward: Decimal
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    explanation: str = ""
    uncertainty_note: str = ""
    master_score: float = 0.0
    score_breakdown: ScoreBreakdown | None = None
    ai_reasoning_id: UUID | None = None
    user_id: UUID | None = None  # None = platform-wide
    status: RecommendationStatus = RecommendationStatus.ACTIVE

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise InvariantViolation(f"confidence out of range: {self.confidence}")
        if self.confidence >= 0.99:
            raise InvariantViolation("recommendations must never claim certainty")
        if not self.uncertainty_note.strip():
            raise InvariantViolation("uncertainty_note is required — explain what could go wrong")
        if not self.explanation.strip():
            raise InvariantViolation("explanation is required — the WHY is the product")
        if not 0.0 <= self.master_score <= 100.0:
            raise InvariantViolation(f"master_score out of range: {self.master_score}")
        if self.action in (Action.STRONG_BUY, Action.BUY):
            self._validate_long_ladder()

    def _validate_long_ladder(self) -> None:
        if not self.stop_loss < self.entry_zone.low:
            raise InvariantViolation("stop loss must sit below the entry zone")
        if not self.entry_zone.high < self.take_profit_1 <= self.take_profit_2 <= self.take_profit_3:
            raise InvariantViolation("take-profit ladder must ascend above the entry zone")

    def supersede(self) -> None:
        self.status = RecommendationStatus.SUPERSEDED
        self.touch()

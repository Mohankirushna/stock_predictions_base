from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.common.entity import AggregateRoot


class AlertType(StrEnum):
    SENTIMENT_SHIFT = "sentiment_shift"
    BREAKOUT = "breakout"
    SUPPORT_BREAK = "support_break"
    RESISTANCE_BREAK = "resistance_break"
    VOLUME_SPIKE = "volume_spike"
    ANALYST_UPGRADE = "analyst_upgrade"
    CONFIDENCE_CHANGE = "confidence_change"
    PRICE_TARGET = "price_target"


@dataclass(kw_only=True, eq=False)
class Alert(AggregateRoot):
    user_id: UUID
    company_id: UUID
    alert_type: AlertType
    condition: dict[str, Any] = field(default_factory=dict)  # e.g. {"price_above": 190}
    is_active: bool = True
    cooldown_minutes: int = 60
    last_triggered_at: datetime | None = None

    def can_trigger(self, now: datetime) -> bool:
        """Active and outside the cooldown window — prevents alert storms."""
        if not self.is_active:
            return False
        if self.last_triggered_at is None:
            return True
        return now >= self.last_triggered_at + timedelta(minutes=self.cooldown_minutes)

    def mark_triggered(self, now: datetime) -> None:
        self.last_triggered_at = now
        self.touch()

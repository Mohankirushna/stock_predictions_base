from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.domain.alerting.alert import Alert
    from app.domain.alerting.notification import Notification


class CreateAlertRequest(BaseModel):
    symbol: str
    alert_type: str = Field(
        pattern="^(sentiment_shift|breakout|support_break|resistance_break|volume_spike|"
        "analyst_upgrade|confidence_change|price_target)$"
    )
    condition: dict[str, Any] = Field(default_factory=dict)
    cooldown_minutes: int = Field(default=60, ge=1, le=10080)


class UpdateAlertRequest(BaseModel):
    is_active: bool | None = None
    condition: dict[str, Any] | None = None
    cooldown_minutes: int | None = Field(default=None, ge=1, le=10080)


class AlertOut(BaseModel):
    id: UUID
    symbol: str
    alert_type: str
    condition: dict[str, Any]
    is_active: bool
    cooldown_minutes: int
    last_triggered_at: datetime | None

    @classmethod
    def from_domain(cls, a: "Alert", symbol: str) -> "AlertOut":
        return cls(
            id=a.id, symbol=symbol, alert_type=a.alert_type.value, condition=a.condition,
            is_active=a.is_active, cooldown_minutes=a.cooldown_minutes, last_triggered_at=a.last_triggered_at,
        )


class NotificationOut(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime

    @classmethod
    def from_domain(cls, n: "Notification") -> "NotificationOut":
        return cls(
            id=n.id, type=n.type, title=n.title, body=n.body, payload=n.payload,
            read_at=n.read_at, created_at=n.created_at,
        )

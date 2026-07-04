from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.common.entity import Entity


class Channel(StrEnum):
    WS = "ws"
    EMAIL = "email"


@dataclass(kw_only=True, eq=False)
class Notification(Entity):
    user_id: UUID
    type: str
    title: str
    body: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    channel: Channel = Channel.WS
    alert_id: UUID | None = None
    sent_at: datetime | None = None
    read_at: datetime | None = None

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self, at: datetime) -> None:
        if self.read_at is None:
            self.read_at = at
            self.touch()

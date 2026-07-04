from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.common.entity import Entity


class EventType(StrEnum):
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    SPLIT = "split"
    FED_MEETING = "fed_meeting"
    CPI = "cpi"
    MACRO = "macro"
    OTHER = "other"


@dataclass(kw_only=True, eq=False)
class MarketEvent(Entity):
    event_type: EventType
    title: str
    scheduled_at: datetime
    company_id: UUID | None = None  # None for macro-level events
    importance: int = 5  # 0–10
    payload: dict[str, Any] = field(default_factory=dict)

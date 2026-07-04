from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class MarketOverviewOut(BaseModel):
    market_trend: str
    fear_greed: int
    vix: float | None
    oil: float | None
    gold: float | None
    btc: float | None
    narrative: str
    risks: list[str]
    outlook: str


class SectorTrendOut(BaseModel):
    sector: str
    trend: str


class MoverOut(BaseModel):
    symbol: str
    name: str
    price: Decimal
    change_pct: Decimal
    currency: str


class MarketEventOut(BaseModel):
    event_type: str
    title: str
    scheduled_at: datetime
    company_symbol: str | None
    importance: int
    payload: dict[str, Any]


class EarningsCalendarOut(BaseModel):
    date: date
    events: list[MarketEventOut]

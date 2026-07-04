from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.common.errors import InvariantViolation


class PriceInterval(StrEnum):
    M1 = "1m"
    M5 = "5m"
    H1 = "1h"
    D1 = "1d"


@dataclass(frozen=True)
class PriceBar:
    """OHLCV bar — a value object; identity is (company_id, ts, interval)."""

    company_id: UUID
    ts: datetime
    interval: PriceInterval
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise InvariantViolation("prices must be positive")
        if self.volume < 0:
            raise InvariantViolation("volume cannot be negative")
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise InvariantViolation("OHLC out of low/high bounds")

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def change_pct(self) -> Decimal:
        return (self.close - self.open) / self.open * 100

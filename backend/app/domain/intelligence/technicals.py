"""Technical analysis domain objects — produced by the pure-Python
Technical Analysis Agent (no AI involved)."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.market.price import PriceInterval


class Trend(StrEnum):
    STRONG_UP = "strong_up"
    UP = "up"
    NEUTRAL = "neutral"
    DOWN = "down"
    STRONG_DOWN = "strong_down"


@dataclass(frozen=True)
class Level:
    """A support or resistance level with how often price respected it."""

    price: Decimal
    strength: int  # touch count


@dataclass(frozen=True)
class Signals:
    golden_cross: bool = False
    death_cross: bool = False
    breakout: bool = False
    breakdown: bool = False
    volume_spike: bool = False
    patterns: tuple[str, ...] = ()  # e.g. "double_bottom", "head_and_shoulders"

    def any_active(self) -> bool:
        return bool(
            self.golden_cross
            or self.death_cross
            or self.breakout
            or self.breakdown
            or self.volume_spike
            or self.patterns
        )


@dataclass(kw_only=True)
class TechnicalSnapshot:
    """Latest computed indicator state for one company + interval."""

    company_id: UUID
    interval: PriceInterval
    computed_at: datetime
    ema_20: Decimal | None = None
    ema_50: Decimal | None = None
    ema_200: Decimal | None = None
    rsi_14: Decimal | None = None
    macd: Decimal | None = None
    macd_signal: Decimal | None = None
    macd_hist: Decimal | None = None
    atr_14: Decimal | None = None
    vwap: Decimal | None = None
    bb_upper: Decimal | None = None
    bb_mid: Decimal | None = None
    bb_lower: Decimal | None = None
    support: list[Level] = field(default_factory=list)
    resistance: list[Level] = field(default_factory=list)
    trend: Trend = Trend.NEUTRAL
    signals: Signals = field(default_factory=Signals)

    @property
    def rsi_zone(self) -> str:
        if self.rsi_14 is None:
            return "unknown"
        if self.rsi_14 >= 70:
            return "overbought"
        if self.rsi_14 <= 30:
            return "oversold"
        return "neutral"

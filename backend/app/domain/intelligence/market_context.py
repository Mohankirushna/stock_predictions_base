"""Market-wide context — output of the Market Intelligence Agent (Agent 5).

Cached (Redis) rather than table-persisted: it's a rolling snapshot the
Research/Recommendation agents read for the macro component of the master
score, not per-company history. Macro *events* (Fed meetings, CPI...) do
persist to the market_events table.
"""
from dataclasses import asdict, dataclass, field
from typing import Any

from app.domain.intelligence.technicals import Trend

CACHE_KEY = "market:context"


@dataclass(frozen=True)
class MarketContext:
    market_trend: Trend
    fear_greed: int  # 0 (extreme fear) .. 100 (extreme greed)
    vix: float | None = None
    interest_rate_pct: float | None = None
    oil: float | None = None
    gold: float | None = None
    btc: float | None = None
    sector_trends: dict[str, str] = field(default_factory=dict)
    narrative: str = ""
    risks: tuple[str, ...] = ()
    outlook: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["market_trend"] = self.market_trend.value
        data["risks"] = list(self.risks)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketContext":
        return cls(
            market_trend=Trend(data["market_trend"]),
            fear_greed=data["fear_greed"],
            vix=data.get("vix"),
            interest_rate_pct=data.get("interest_rate_pct"),
            oil=data.get("oil"),
            gold=data.get("gold"),
            btc=data.get("btc"),
            sector_trends=dict(data.get("sector_trends", {})),
            narrative=data.get("narrative", ""),
            risks=tuple(data.get("risks", ())),
            outlook=data.get("outlook", ""),
        )

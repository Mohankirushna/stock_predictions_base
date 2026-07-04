"""Opportunity Discovery output — a lightweight, AI-ranked screening result
for companies not currently on any watchlist.

Deliberately NOT a formal Recommendation: no stop-loss/take-profit ladder
rigor. That formal scoring is the Recommendation Agent's job (M14), which
reads this output alongside every other agent's. Cached in Redis (see
CACHE_KEY), not table-persisted — a rolling cross-company snapshot, not one
company's history, mirroring MarketContext's (M11) storage pattern.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.common.errors import InvariantViolation

CACHE_KEY = "opportunities:latest"


@dataclass(frozen=True)
class OpportunityCandidate:
    symbol: str
    company_name: str
    reasons: tuple[str, ...]
    confidence: float  # 0.0-1.0 — the AI's confidence in this pick, never certainty
    catalysts: tuple[str, ...]
    risk: str
    entry_zone_low: Decimal
    entry_zone_high: Decimal

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise InvariantViolation(f"confidence out of range: {self.confidence}")
        if self.confidence >= 0.99:
            raise InvariantViolation("opportunities must never claim certainty")
        if not self.reasons:
            raise InvariantViolation("at least one reason is required")
        if not self.risk.strip():
            raise InvariantViolation("risk must not be empty — every opportunity has one")
        if self.entry_zone_low <= 0 or self.entry_zone_high <= 0:
            raise InvariantViolation("entry zone prices must be positive")
        if self.entry_zone_low > self.entry_zone_high:
            raise InvariantViolation("entry zone low must not exceed high")

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "company_name": self.company_name,
            "reasons": list(self.reasons), "confidence": self.confidence,
            "catalysts": list(self.catalysts), "risk": self.risk,
            "entry_zone_low": str(self.entry_zone_low), "entry_zone_high": str(self.entry_zone_high),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpportunityCandidate":
        return cls(
            symbol=data["symbol"], company_name=data["company_name"],
            reasons=tuple(data["reasons"]), confidence=data["confidence"],
            catalysts=tuple(data["catalysts"]), risk=data["risk"],
            entry_zone_low=Decimal(data["entry_zone_low"]),
            entry_zone_high=Decimal(data["entry_zone_high"]),
        )

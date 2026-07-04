"""Agent 9 — Portfolio analytics math. Pure Python, no AI: P&L, allocation,
sector exposure, a diversification score (Herfindahl-Hirschman-based), a
risk score, a letter health grade, and rebalancing suggestions.

Keyed by company symbol throughout — these are display-facing computations,
not domain entities with invariants, so plain dicts/floats are appropriate.
"""
from dataclasses import dataclass
from decimal import Decimal

_MAX_POSITION_PCT = 25.0
_MAX_SECTOR_PCT = 40.0


@dataclass(frozen=True)
class HoldingView:
    symbol: str
    sector: str
    quantity: Decimal
    avg_cost: Decimal
    price: Decimal

    @property
    def market_value(self) -> Decimal:
        return self.quantity * self.price

    @property
    def unrealized_pnl(self) -> Decimal:
        return (self.price - self.avg_cost) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        return float((self.price - self.avg_cost) / self.avg_cost * 100)


def total_value(holdings: list[HoldingView], cash_balance: Decimal) -> Decimal:
    return sum((h.market_value for h in holdings), Decimal("0")) + cash_balance


def total_unrealized_pnl(holdings: list[HoldingView]) -> Decimal:
    return sum((h.unrealized_pnl for h in holdings), Decimal("0"))


def allocation_pct(holdings: list[HoldingView], total: Decimal) -> dict[str, float]:
    if total <= 0:
        return {}
    return {h.symbol: float(h.market_value / total * 100) for h in holdings}


def sector_exposure_pct(holdings: list[HoldingView], total: Decimal) -> dict[str, float]:
    if total <= 0:
        return {}
    exposure: dict[str, Decimal] = {}
    for h in holdings:
        sector = h.sector or "Unknown"
        exposure[sector] = exposure.get(sector, Decimal("0")) + h.market_value
    return {sector: float(value / total * 100) for sector, value in exposure.items()}


def diversification_score(allocation: dict[str, float]) -> float:
    """100 - normalized Herfindahl-Hirschman Index: many small equal
    positions score near 100; a single concentrated position scores near 0."""
    if not allocation:
        return 100.0
    hhi = sum((pct / 100) ** 2 for pct in allocation.values())
    return round((1 - hhi) * 100, 2)


def risk_score(sector_exposure: dict[str, float], diversification: float) -> float:
    """Higher = safer. Starts from diversification, then penalizes any
    single sector exceeding the concentration guideline."""
    score = diversification
    if sector_exposure:
        max_sector = max(sector_exposure.values())
        if max_sector > _MAX_SECTOR_PCT:
            score -= max_sector - _MAX_SECTOR_PCT
    return max(0.0, min(100.0, score))


def health_grade(risk: float, diversification: float, unrealized_pnl_pct: float) -> str:
    composite = (risk + diversification) / 2 + (5 if unrealized_pnl_pct > 0 else -5)
    if composite >= 80:
        return "A"
    if composite >= 65:
        return "B"
    if composite >= 50:
        return "C"
    if composite >= 35:
        return "D"
    return "F"


def rebalancing_suggestions(allocation: dict[str, float], sector_exposure: dict[str, float]) -> list[str]:
    suggestions = [
        f"Consider trimming {symbol} — {pct:.1f}% of the portfolio exceeds the "
        f"{_MAX_POSITION_PCT:.0f}% single-position guideline."
        for symbol, pct in allocation.items()
        if pct > _MAX_POSITION_PCT
    ]
    suggestions += [
        f"{sector} is {pct:.1f}% of the portfolio — consider diversifying beyond "
        f"the {_MAX_SECTOR_PCT:.0f}% sector guideline."
        for sector, pct in sector_exposure.items()
        if pct > _MAX_SECTOR_PCT
    ]
    if not suggestions:
        suggestions.append("Allocation looks reasonably balanced; no rebalancing action suggested.")
    return suggestions

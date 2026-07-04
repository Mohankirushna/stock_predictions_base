"""Deterministic macro indicator computation — the NO-AI half of Agent 5.

Macro readings come from liquid proxy ETFs quoted by the regular
MarketDataSource (no separate macro feed needed on free vendor tiers):
SPY/QQQ (market trend), VIXY (volatility), USO (oil), GLD (gold),
BITO (bitcoin), and sector SPDRs for sector trends.

Fear & Greed here is a simplified, transparent formula over breadth and
volatility — NOT CNN's proprietary 7-component index.
"""
from decimal import Decimal

from app.domain.intelligence.technicals import Trend
from app.domain.ports.market_data_source import Quote

MARKET_PROXIES = ("SPY", "QQQ")
VOLATILITY_PROXY = "VIXY"
COMMODITY_PROXIES = {"oil": "USO", "gold": "GLD", "btc": "BITO"}
SECTOR_PROXIES = {
    "Technology": "XLK", "Financials": "XLF", "Energy": "XLE", "Healthcare": "XLV",
    "Consumer Discretionary": "XLY", "Industrials": "XLI", "Utilities": "XLU",
}


def classify_market_trend(changes_pct: list[Decimal]) -> Trend:
    """Average day-change across market proxies, banded."""
    if not changes_pct:
        return Trend.NEUTRAL
    avg = float(sum(changes_pct) / len(changes_pct))
    if avg >= 1.5:
        return Trend.STRONG_UP
    if avg >= 0.3:
        return Trend.UP
    if avg <= -1.5:
        return Trend.STRONG_DOWN
    if avg <= -0.3:
        return Trend.DOWN
    return Trend.NEUTRAL


def classify_sector_trends(quotes_by_symbol: dict[str, Quote]) -> dict[str, str]:
    trends: dict[str, str] = {}
    for sector, proxy in SECTOR_PROXIES.items():
        quote = quotes_by_symbol.get(proxy)
        if quote is not None:
            trends[sector] = classify_market_trend([quote.change_pct]).value
    return trends


def compute_fear_greed(market_changes_pct: list[Decimal], volatility_change_pct: Decimal | None) -> int:
    """0 = extreme fear, 100 = extreme greed. 50 is neutral; market strength
    pushes up, rising volatility pushes down. Clamped, transparent, simple."""
    score = 50.0
    if market_changes_pct:
        score += float(sum(market_changes_pct) / len(market_changes_pct)) * 10
    if volatility_change_pct is not None:
        score -= float(volatility_change_pct) * 5
    return max(0, min(100, round(score)))

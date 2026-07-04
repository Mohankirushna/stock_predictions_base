"""Institutional-buying component — the one score input that isn't read
from persisted tables. Analyst ratings and insider trades have no
dedicated tables in this schema (per M6's design note), so the
Recommendation Agent fetches them live from MarketDataSource at scoring
time and this function scores them directly.
"""
from typing import Any


def institutional_score(analyst_ratings: list[dict[str, Any]], insider_trades: list[dict[str, Any]]) -> float:
    if not analyst_ratings and not insider_trades:
        return 50.0

    score = 50.0
    if analyst_ratings:
        latest = analyst_ratings[0]  # vendor returns most-recent-period first
        buy = latest.get("strongBuy", 0) + latest.get("buy", 0)
        total = buy + latest.get("hold", 0) + latest.get("sell", 0) + latest.get("strongSell", 0)
        if total > 0:
            score = (buy / total) * 100

    if insider_trades:
        net_shares = sum(t.get("change", 0) or 0 for t in insider_trades)
        if net_shares > 0:
            score += 10
        elif net_shares < 0:
            score -= 10

    return max(0.0, min(100.0, score))

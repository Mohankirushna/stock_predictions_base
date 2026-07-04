"""Agent 10 — per-alert-type trigger checks. Pure Python: each function
reads currently-available state and returns a (triggered, message) pair.
Two alert types (ANALYST_UPGRADE, CONFIDENCE_CHANGE) are necessarily
simplified — this schema has no historical rating/confidence snapshots to
diff against, so they check the current reading against a threshold in the
alert's `condition` rather than detecting a genuine change.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.intelligence.news import NewsArticle
from app.domain.intelligence.technicals import TechnicalSnapshot
from app.domain.market.price import PriceBar
from app.domain.research.recommendation import Recommendation


@dataclass(frozen=True)
class CheckResult:
    triggered: bool
    message: str = ""


def check_sentiment_shift(news: list[NewsArticle], condition: dict[str, Any]) -> CheckResult:
    threshold = condition.get("min_abs_sentiment", 0.5)
    analyzed = [a for a in news if a.is_analyzed]
    if not analyzed:
        return CheckResult(False)
    latest = analyzed[0]
    if abs(latest.analysis.sentiment) >= threshold:
        direction = "positive" if latest.analysis.sentiment > 0 else "negative"
        return CheckResult(True, f"Sentiment shifted sharply {direction} ({latest.analysis.sentiment:+.2f}).")
    return CheckResult(False)


def check_breakout(technicals: TechnicalSnapshot | None, condition: dict[str, Any]) -> CheckResult:
    if technicals and technicals.signals.breakout:
        return CheckResult(True, "Price broke out above resistance.")
    return CheckResult(False)


def check_support_break(technicals: TechnicalSnapshot | None, condition: dict[str, Any]) -> CheckResult:
    if technicals and technicals.signals.breakdown:
        return CheckResult(True, "Price broke down below support.")
    return CheckResult(False)


def check_resistance_break(technicals: TechnicalSnapshot | None, condition: dict[str, Any]) -> CheckResult:
    if technicals and technicals.signals.breakout:
        return CheckResult(True, "Price broke above a key resistance level.")
    return CheckResult(False)


def check_volume_spike(technicals: TechnicalSnapshot | None, condition: dict[str, Any]) -> CheckResult:
    if technicals and technicals.signals.volume_spike:
        return CheckResult(True, "Unusual volume spike detected.")
    return CheckResult(False)


def check_analyst_upgrade(analyst_ratings: list[dict[str, Any]], condition: dict[str, Any]) -> CheckResult:
    min_buy_ratio = condition.get("min_buy_ratio", 0.7)
    if not analyst_ratings:
        return CheckResult(False)
    latest = analyst_ratings[0]
    buy = latest.get("strongBuy", 0) + latest.get("buy", 0)
    total = buy + latest.get("hold", 0) + latest.get("sell", 0) + latest.get("strongSell", 0)
    if total > 0 and (buy / total) >= min_buy_ratio:
        return CheckResult(True, f"Analyst sentiment is strongly bullish ({buy}/{total} buy-rated).")
    return CheckResult(False)


def check_confidence_change(recommendation: Recommendation | None, condition: dict[str, Any]) -> CheckResult:
    min_confidence = condition.get("min_confidence", 0.75)
    if recommendation and recommendation.confidence >= min_confidence:
        return CheckResult(True, f"AI confidence reached {recommendation.confidence:.0%} on the active recommendation.")
    return CheckResult(False)


def check_price_target(latest_bar: PriceBar | None, condition: dict[str, Any]) -> CheckResult:
    target = condition.get("target_price")
    direction = condition.get("direction", "above")
    if latest_bar is None or target is None:
        return CheckResult(False)
    target = Decimal(str(target))
    if direction == "above" and latest_bar.close >= target:
        return CheckResult(True, f"Price reached {latest_bar.close}, at or above target {target}.")
    if direction == "below" and latest_bar.close <= target:
        return CheckResult(True, f"Price fell to {latest_bar.close}, at or below target {target}.")
    return CheckResult(False)

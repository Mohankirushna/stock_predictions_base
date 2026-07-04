from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.application.agents.alert import checks
from app.domain.common.values import PriceRange
from app.domain.intelligence.news import NewsAnalysis, NewsArticle
from app.domain.intelligence.technicals import Signals, TechnicalSnapshot, Trend
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.research.recommendation import Action, HoldingPeriod, Recommendation


def _article(sentiment: float) -> NewsArticle:
    a = NewsArticle(source="s", url=f"https://x/{uuid4().hex}", title="t")
    a.analysis = NewsAnalysis(sentiment=sentiment, importance=5, summary="s")
    return a


def _technicals(**overrides) -> TechnicalSnapshot:
    defaults = dict(
        company_id=uuid4(), interval=PriceInterval.D1, computed_at=datetime.now(UTC),
        trend=Trend.NEUTRAL, signals=Signals(),
    )
    defaults.update(overrides)
    return TechnicalSnapshot(**defaults)


def _bar(close: str) -> PriceBar:
    return PriceBar(
        company_id=uuid4(), ts=datetime.now(UTC), interval=PriceInterval.D1,
        open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close),
        volume=Decimal("100"),
    )


def _recommendation(confidence: float) -> Recommendation:
    return Recommendation(
        company_id=uuid4(), action=Action.HOLD, current_price=Decimal("100"),
        entry_zone=PriceRange(Decimal("95"), Decimal("100")), stop_loss=Decimal("90"),
        take_profit_1=Decimal("110"), take_profit_2=Decimal("115"), take_profit_3=Decimal("120"),
        holding_period=HoldingPeriod.MEDIUM, confidence=confidence, risk_reward=Decimal("1.5"),
        explanation="x", uncertainty_note="y",
    )


def test_sentiment_shift_triggers_above_threshold() -> None:
    result = checks.check_sentiment_shift([_article(-0.8)], {"min_abs_sentiment": 0.5})
    assert result.triggered is True
    assert "negative" in result.message


def test_sentiment_shift_no_trigger_below_threshold() -> None:
    assert checks.check_sentiment_shift([_article(0.1)], {"min_abs_sentiment": 0.5}).triggered is False


def test_sentiment_shift_no_articles() -> None:
    assert checks.check_sentiment_shift([], {}).triggered is False


def test_breakout_triggers_on_signal() -> None:
    assert checks.check_breakout(_technicals(signals=Signals(breakout=True)), {}).triggered is True


def test_breakout_no_trigger_without_signal() -> None:
    assert checks.check_breakout(_technicals(), {}).triggered is False


def test_breakout_none_technicals() -> None:
    assert checks.check_breakout(None, {}).triggered is False


def test_support_break_triggers_on_breakdown() -> None:
    assert checks.check_support_break(_technicals(signals=Signals(breakdown=True)), {}).triggered is True


def test_volume_spike_triggers() -> None:
    assert checks.check_volume_spike(_technicals(signals=Signals(volume_spike=True)), {}).triggered is True


def test_analyst_upgrade_triggers_on_high_buy_ratio() -> None:
    ratings = [{"strongBuy": 15, "buy": 5, "hold": 0, "sell": 0, "strongSell": 0}]
    result = checks.check_analyst_upgrade(ratings, {"min_buy_ratio": 0.7})
    assert result.triggered is True


def test_analyst_upgrade_no_trigger_below_ratio() -> None:
    ratings = [{"strongBuy": 2, "buy": 2, "hold": 6, "sell": 0, "strongSell": 0}]
    assert checks.check_analyst_upgrade(ratings, {"min_buy_ratio": 0.7}).triggered is False


def test_analyst_upgrade_no_ratings() -> None:
    assert checks.check_analyst_upgrade([], {}).triggered is False


def test_confidence_change_triggers_above_threshold() -> None:
    result = checks.check_confidence_change(_recommendation(0.85), {"min_confidence": 0.75})
    assert result.triggered is True


def test_confidence_change_no_recommendation() -> None:
    assert checks.check_confidence_change(None, {}).triggered is False


def test_price_target_above_direction() -> None:
    result = checks.check_price_target(_bar("205"), {"target_price": 200, "direction": "above"})
    assert result.triggered is True


def test_price_target_below_direction() -> None:
    result = checks.check_price_target(_bar("95"), {"target_price": 100, "direction": "below"})
    assert result.triggered is True


def test_price_target_not_reached() -> None:
    result = checks.check_price_target(_bar("150"), {"target_price": 200, "direction": "above"})
    assert result.triggered is False


def test_price_target_missing_condition() -> None:
    assert checks.check_price_target(_bar("150"), {}).triggered is False

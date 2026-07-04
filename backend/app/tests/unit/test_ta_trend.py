from app.application.agents.technical_analysis.trend import classify_trend
from app.domain.intelligence.technicals import Trend


def test_strong_uptrend() -> None:
    assert classify_trend(close=110, ema20=105, ema50=100, ema200=90) is Trend.STRONG_UP


def test_uptrend() -> None:
    assert classify_trend(close=102, ema20=100, ema50=101, ema200=95) is Trend.UP


def test_strong_downtrend() -> None:
    assert classify_trend(close=80, ema20=85, ema50=90, ema200=100) is Trend.STRONG_DOWN


def test_downtrend() -> None:
    assert classify_trend(close=88, ema20=90, ema50=89, ema200=95) is Trend.DOWN


def test_neutral_when_emas_are_mixed() -> None:
    assert classify_trend(close=100, ema20=101, ema50=99, ema200=100) is Trend.NEUTRAL


def test_neutral_when_any_ema_missing() -> None:
    assert classify_trend(close=100, ema20=None, ema50=99, ema200=95) is Trend.NEUTRAL

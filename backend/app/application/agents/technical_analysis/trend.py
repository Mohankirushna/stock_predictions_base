"""Trend classification — a transparent rule over EMA stacking, not a model."""
from app.domain.intelligence.technicals import Trend


def classify_trend(close: float, ema20: float | None, ema50: float | None, ema200: float | None) -> Trend:
    if ema20 is None or ema50 is None or ema200 is None:
        return Trend.NEUTRAL
    if close > ema20 > ema50 > ema200:
        return Trend.STRONG_UP
    if close > ema50 > ema200:
        return Trend.UP
    if close < ema20 < ema50 < ema200:
        return Trend.STRONG_DOWN
    if close < ema50 < ema200:
        return Trend.DOWN
    return Trend.NEUTRAL

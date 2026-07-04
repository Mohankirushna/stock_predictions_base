"""Signal detection: EMA crosses, breakouts, volume spikes, and a small set
of deterministic candlestick patterns. No AI, no fuzzy heuristics."""
from statistics import mean


def detect_golden_death_cross(ema50_series: list[float], ema200_series: list[float]) -> tuple[bool, bool]:
    """Compares the last two points of each series — a cross happened
    between the previous and current bar. Returns (golden_cross, death_cross)."""
    if len(ema50_series) < 2 or len(ema200_series) < 2:
        return False, False
    prev_diff = ema50_series[-2] - ema200_series[-2]
    curr_diff = ema50_series[-1] - ema200_series[-1]
    return prev_diff <= 0 < curr_diff, prev_diff >= 0 > curr_diff


def detect_breakout(latest_close: float, resistance_prices: list[float]) -> bool:
    return bool(resistance_prices) and latest_close > max(resistance_prices)


def detect_breakdown(latest_close: float, support_prices: list[float]) -> bool:
    return bool(support_prices) and latest_close < min(support_prices)


def detect_volume_spike(volumes: list[float], *, lookback: int = 20, multiplier: float = 2.0) -> bool:
    if len(volumes) < lookback + 1:
        return False
    baseline = mean(volumes[-lookback - 1 : -1])
    return baseline > 0 and volumes[-1] > baseline * multiplier


def detect_candlestick_patterns(
    opens: list[float], highs: list[float], lows: list[float], closes: list[float]
) -> list[str]:
    """Last-two-bar heuristics: doji on the latest bar, plus bullish/bearish
    engulfing across the last two bars."""
    patterns: list[str] = []
    if closes:
        o, h, low, c = opens[-1], highs[-1], lows[-1], closes[-1]
        candle_range = h - low
        if candle_range > 0 and abs(c - o) / candle_range < 0.1:
            patterns.append("doji")

    if len(closes) >= 2:
        prev_o, prev_c, o, c = opens[-2], closes[-2], opens[-1], closes[-1]
        if prev_c < prev_o and c > o and c > prev_o and o < prev_c:
            patterns.append("bullish_engulfing")
        if prev_c > prev_o and c < o and o > prev_c and c < prev_o:
            patterns.append("bearish_engulfing")

    return patterns

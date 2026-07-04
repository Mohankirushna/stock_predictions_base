"""Pure-Python technical indicators — no AI, no external services.

All functions take a chronological (oldest→newest) list of floats and
return either a single latest value or a full series, as noted per
function. `None` (or an empty series) means "not enough history yet."
"""
from statistics import mean


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return mean(values[-period:])


def ema_series(values: list[float], period: int) -> list[float]:
    """Full EMA series — needed (not just the latest value) to detect
    golden/death crosses, which compare two EMA series over time."""
    if len(values) < period:
        return []
    multiplier = 2 / (period + 1)
    series = [mean(values[:period])]
    for price in values[period:]:
        series.append((price - series[-1]) * multiplier + series[-1])
    return series


def ema(values: list[float], period: int) -> float | None:
    series = ema_series(values, period)
    return series[-1] if series else None


def rsi(values: list[float], period: int = 14) -> float | None:
    """Wilder's RSI: average gain/loss seeded from the first `period`
    changes, then smoothed forward."""
    if len(values) < period + 1:
        return None
    gains = [max(values[i] - values[i - 1], 0.0) for i in range(1, len(values))]
    losses = [max(values[i - 1] - values[i], 0.0) for i in range(1, len(values))]

    avg_gain, avg_loss = mean(gains[:period]), mean(losses[:period])
    for gain, loss in zip(gains[period:], losses[period:], strict=True):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(
    values: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float, float, float] | None:
    """Returns (macd_line, signal_line, histogram), or None if there isn't
    enough history for the signal line to warm up."""
    if len(values) < slow + signal:
        return None
    fast_series, slow_series = ema_series(values, fast), ema_series(values, slow)
    offset = len(fast_series) - len(slow_series)  # slow EMA warms up later
    macd_line = [f - s for f, s in zip(fast_series[offset:], slow_series, strict=True)]
    signal_series = ema_series(macd_line, signal)
    if not signal_series:
        return None
    macd_val, signal_val = macd_line[-1], signal_series[-1]
    return macd_val, signal_val, macd_val - signal_val


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    """Average True Range, Wilder-smoothed."""
    if len(closes) < period + 1:
        return None
    true_ranges = [
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        for i in range(1, len(closes))
    ]
    value = mean(true_ranges[:period])
    for tr in true_ranges[period:]:
        value = (value * (period - 1) + tr) / period
    return value


def vwap(highs: list[float], lows: list[float], closes: list[float], volumes: list[float]) -> float | None:
    """Volume-weighted average price over the whole supplied window."""
    if not closes:
        return None
    total_volume = sum(volumes)
    if total_volume == 0:
        return None
    typical = [(h + low + c) / 3 for h, low, c in zip(highs, lows, closes, strict=True)]
    return sum(tp * v for tp, v in zip(typical, volumes, strict=True)) / total_volume


def bollinger_bands(
    values: list[float], period: int = 20, num_std: float = 2.0
) -> tuple[float, float, float] | None:
    """Returns (upper, mid, lower) around the SMA, or None if not enough history."""
    if len(values) < period:
        return None
    window = values[-period:]
    mid = mean(window)
    variance = mean((v - mid) ** 2 for v in window)
    std = variance**0.5
    return mid + num_std * std, mid, mid - num_std * std

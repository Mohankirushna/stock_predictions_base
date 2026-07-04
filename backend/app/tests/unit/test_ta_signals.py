from app.application.agents.technical_analysis import signals


def test_golden_cross_detected_when_ema50_crosses_above_ema200() -> None:
    ema50 = [95, 101]
    ema200 = [100, 100]
    golden, death = signals.detect_golden_death_cross(ema50, ema200)
    assert golden is True
    assert death is False


def test_death_cross_detected_when_ema50_crosses_below_ema200() -> None:
    ema50 = [105, 99]
    ema200 = [100, 100]
    golden, death = signals.detect_golden_death_cross(ema50, ema200)
    assert golden is False
    assert death is True


def test_no_cross_when_no_sign_change() -> None:
    golden, death = signals.detect_golden_death_cross([105, 106], [100, 100])
    assert (golden, death) == (False, False)


def test_cross_requires_at_least_two_points() -> None:
    assert signals.detect_golden_death_cross([105], [100]) == (False, False)


def test_breakout_when_close_exceeds_resistance() -> None:
    assert signals.detect_breakout(110, [100, 105]) is True
    assert signals.detect_breakout(104, [100, 105]) is False


def test_breakout_false_with_no_resistance_levels() -> None:
    assert signals.detect_breakout(110, []) is False


def test_breakdown_when_close_below_support() -> None:
    assert signals.detect_breakdown(90, [95, 100]) is True
    assert signals.detect_breakdown(96, [95, 100]) is False


def test_volume_spike_detected_above_multiplier() -> None:
    volumes = [100] * 20 + [300]  # 3x the 100-avg baseline
    assert signals.detect_volume_spike(volumes, lookback=20, multiplier=2.0) is True


def test_volume_spike_not_detected_within_normal_range() -> None:
    volumes = [100] * 20 + [150]
    assert signals.detect_volume_spike(volumes, lookback=20, multiplier=2.0) is False


def test_volume_spike_insufficient_history_returns_false() -> None:
    assert signals.detect_volume_spike([100, 200], lookback=20) is False


def test_doji_detected_on_small_body() -> None:
    # body=|100.1-100|=0.1, range=101-99=2 -> body/range=0.05 < 0.1
    patterns = signals.detect_candlestick_patterns([100.0], [101.0], [99.0], [100.1])
    assert "doji" in patterns


def test_bullish_engulfing_detected() -> None:
    # prev: bearish candle open=10 close=8; curr: bullish candle open=7 close=11
    opens = [10, 7]
    closes = [8, 11]
    highs = [10.5, 11.5]
    lows = [7.5, 6.5]
    patterns = signals.detect_candlestick_patterns(opens, highs, lows, closes)
    assert "bullish_engulfing" in patterns


def test_bearish_engulfing_detected() -> None:
    # prev: bullish candle open=8 close=10; curr: bearish candle open=11 close=7
    opens = [8, 11]
    closes = [10, 7]
    highs = [10.5, 11.5]
    lows = [7.5, 6.5]
    patterns = signals.detect_candlestick_patterns(opens, highs, lows, closes)
    assert "bearish_engulfing" in patterns


def test_no_pattern_on_plain_single_bar() -> None:
    patterns = signals.detect_candlestick_patterns([100.0], [110.0], [90.0], [105.0])
    assert patterns == []

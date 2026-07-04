"""Every non-trivial expected value here is hand-derived from the formula
(shown in comments), not copied from an external reference — so a broken
implementation fails loudly rather than matching a misremembered constant."""
import pytest

from app.application.agents.technical_analysis import indicators


def test_sma_basic() -> None:
    assert indicators.sma([1, 2, 3, 4, 5], 5) == 3.0


def test_sma_insufficient_data_returns_none() -> None:
    assert indicators.sma([1, 2], 5) is None


def test_ema_matches_hand_computed_series() -> None:
    # seed = mean([1,2,3]) = 2.0; multiplier = 2/(3+1) = 0.5
    # price=4: (4-2.0)*0.5+2.0 = 3.0
    # price=5: (5-3.0)*0.5+3.0 = 4.0
    assert indicators.ema([1, 2, 3, 4, 5], 3) == 4.0


def test_ema_insufficient_data_returns_none() -> None:
    assert indicators.ema([1, 2], 5) is None


def test_rsi_matches_hand_computed_value() -> None:
    # values=[10,12,11,13], period=2
    # changes: +2,-1,+2 -> gains=[2,0,2], losses=[0,1,0]
    # avg_gain=mean([2,0])=1.0, avg_loss=mean([0,1])=0.5
    # smooth with (gain=2,loss=0): avg_gain=(1*1+2)/2=1.5, avg_loss=(0.5*1+0)/2=0.25
    # rs=6.0, rsi=100-100/7=85.71428571428571
    result = indicators.rsi([10, 12, 11, 13], period=2)
    assert result == pytest.approx(600 / 7, abs=1e-9)


def test_rsi_all_gains_is_100() -> None:
    assert indicators.rsi([1, 2, 3, 4, 5], period=3) == 100.0


def test_rsi_insufficient_data_returns_none() -> None:
    assert indicators.rsi([1, 2], period=14) is None


def test_macd_returns_none_when_insufficient_history() -> None:
    assert indicators.macd(list(range(20)), fast=12, slow=26, signal=9) is None


def test_macd_histogram_equals_macd_minus_signal() -> None:
    values = [float(i) + (i % 5) for i in range(60)]
    result = indicators.macd(values)
    assert result is not None
    macd_val, signal_val, hist = result
    assert hist == pytest.approx(macd_val - signal_val)


def test_atr_matches_hand_computed_value() -> None:
    # highs=[10,11,12] lows=[8,9,10] closes=[9,10,11], period=2
    # TR(i=1)=max(11-9=2, |11-9|=2, |9-9|=0)=2
    # TR(i=2)=max(12-10=2, |12-10|=2, |10-10|=0)=2
    # atr = mean([2,2]) = 2.0 (no smoothing beyond seed since only 2 TRs)
    assert indicators.atr([10, 11, 12], [8, 9, 10], [9, 10, 11], period=2) == 2.0


def test_atr_insufficient_data_returns_none() -> None:
    assert indicators.atr([10], [8], [9], period=14) is None


def test_vwap_matches_hand_computed_value() -> None:
    # typical=[(10+8+9)/3=9.0, (12+10+11)/3=11.0]; volumes=[100,200]
    # vwap = (9*100 + 11*200) / 300 = 3100/300 = 10.333...
    result = indicators.vwap([10, 12], [8, 10], [9, 11], [100, 200])
    assert result == pytest.approx(3100 / 300)


def test_vwap_zero_volume_returns_none() -> None:
    assert indicators.vwap([10], [8], [9], [0]) is None


def test_bollinger_bands_matches_hand_computed_value() -> None:
    # values=[1,2,3,4,5], mid=3.0, variance=mean([4,1,0,1,4])=2.0, std=sqrt(2)
    upper, mid, lower = indicators.bollinger_bands([1, 2, 3, 4, 5], period=5, num_std=2.0)
    assert mid == 3.0
    assert upper == pytest.approx(3.0 + 2 * 2**0.5)
    assert lower == pytest.approx(3.0 - 2 * 2**0.5)


def test_bollinger_bands_insufficient_data_returns_none() -> None:
    assert indicators.bollinger_bands([1, 2], period=20) is None

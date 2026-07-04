from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.application.agents.learning import analysis as an
from app.domain.common.values import PriceRange
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.research.prediction import Direction
from app.domain.research.recommendation import Action, HoldingPeriod, Recommendation


def _bar(low: str, high: str) -> PriceBar:
    return PriceBar(
        company_id=uuid4(), ts=datetime.now(UTC), interval=PriceInterval.D1,
        open=Decimal(low), high=Decimal(high), low=Decimal(low), close=Decimal(high),
        volume=Decimal("100"),
    )


def _recommendation(action=Action.BUY, **overrides) -> Recommendation:
    defaults = dict(
        company_id=uuid4(), action=action, current_price=Decimal("100"),
        entry_zone=PriceRange(Decimal("95"), Decimal("100")), stop_loss=Decimal("90"),
        take_profit_1=Decimal("110"), take_profit_2=Decimal("120"), take_profit_3=Decimal("130"),
        holding_period=HoldingPeriod.MEDIUM, confidence=0.6, risk_reward=Decimal("1.5"),
        explanation="x", uncertainty_note="y",
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


def test_direction_up_beyond_band() -> None:
    assert an.determine_actual_direction(Decimal("100"), Decimal("105")) is Direction.UP


def test_direction_down_beyond_band() -> None:
    assert an.determine_actual_direction(Decimal("100"), Decimal("95")) is Direction.DOWN


def test_direction_sideways_within_band() -> None:
    assert an.determine_actual_direction(Decimal("100"), Decimal("101")) is Direction.SIDEWAYS


def test_drawdown_and_gain() -> None:
    bars = [_bar("90", "110"), _bar("85", "115")]
    drawdown, gain = an.compute_drawdown_and_gain(bars, Decimal("100"))
    assert drawdown == Decimal("-15")  # (85-100)/100*100
    assert gain == Decimal("15")  # (115-100)/100*100


def test_drawdown_and_gain_empty_bars() -> None:
    assert an.compute_drawdown_and_gain([], Decimal("100")) == (Decimal("0"), Decimal("0"))


def test_hit_flags_stop_loss() -> None:
    rec = _recommendation()
    bars = [_bar("85", "95")]  # low 85 breaches stop_loss=90
    hits = an.compute_hit_flags(bars, rec)
    assert hits.hit_stop_loss is True
    assert hits.hit_tp1 is False


def test_hit_flags_all_targets() -> None:
    rec = _recommendation()
    bars = [_bar("95", "135")]  # high 135 clears all three targets
    hits = an.compute_hit_flags(bars, rec)
    assert hits == an.HitFlags(hit_stop_loss=False, hit_tp1=True, hit_tp2=True, hit_tp3=True)


def test_hit_flags_not_a_long_action_reports_no_hits() -> None:
    rec = _recommendation(action=Action.HOLD)
    bars = [_bar("50", "200")]
    assert an.compute_hit_flags(bars, rec) == an.HitFlags(False, False, False, False)


def test_accuracy_score_stopped_out_is_zero_even_if_direction_correct() -> None:
    hits = an.HitFlags(hit_stop_loss=True, hit_tp1=False, hit_tp2=False, hit_tp3=False)
    assert an.compute_accuracy_score(direction_correct=True, hits=hits) == 0.0


def test_accuracy_score_direction_correct_no_targets() -> None:
    hits = an.HitFlags(False, False, False, False)
    assert an.compute_accuracy_score(direction_correct=True, hits=hits) == 0.5


def test_accuracy_score_full_credit() -> None:
    hits = an.HitFlags(False, True, True, True)
    assert an.compute_accuracy_score(direction_correct=True, hits=hits) == 1.0


def test_rolling_accuracy_first_sample() -> None:
    result = an.update_rolling_accuracy({}, 0.8)
    assert result == {"rolling_accuracy": 0.8, "sample_size": 1}


def test_rolling_accuracy_running_mean() -> None:
    result = an.update_rolling_accuracy({"rolling_accuracy": 0.6, "sample_size": 2}, 0.9)
    # (0.6*2 + 0.9) / 3 = 2.1/3 = 0.7
    assert result == {"rolling_accuracy": 0.7, "sample_size": 3}

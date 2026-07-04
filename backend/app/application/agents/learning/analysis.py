"""Agent 11 — evaluation math. Pure Python: how a prediction actually
played out against the price history since it was made."""
from dataclasses import dataclass
from decimal import Decimal

from app.domain.market.price import PriceBar
from app.domain.research.prediction import Direction
from app.domain.research.recommendation import Action, Recommendation

_SIDEWAYS_BAND_PCT = Decimal("2.0")  # within +/-2% counts as "sideways", not a direction call


@dataclass(frozen=True)
class HitFlags:
    hit_stop_loss: bool
    hit_tp1: bool
    hit_tp2: bool
    hit_tp3: bool


def determine_actual_direction(price_at_prediction: Decimal, actual_price: Decimal) -> Direction:
    if price_at_prediction <= 0:
        return Direction.SIDEWAYS
    change_pct = (actual_price - price_at_prediction) / price_at_prediction * 100
    if change_pct > _SIDEWAYS_BAND_PCT:
        return Direction.UP
    if change_pct < -_SIDEWAYS_BAND_PCT:
        return Direction.DOWN
    return Direction.SIDEWAYS


def compute_drawdown_and_gain(bars: list[PriceBar], reference_price: Decimal) -> tuple[Decimal, Decimal]:
    """Returns (max_drawdown_pct, max_gain_pct) over the bar window,
    relative to the price at prediction time. Drawdown is <= 0."""
    if not bars or reference_price <= 0:
        return Decimal("0"), Decimal("0")
    max_drawdown = min((b.low - reference_price) / reference_price * 100 for b in bars)
    max_gain = max((b.high - reference_price) / reference_price * 100 for b in bars)
    return min(max_drawdown, Decimal("0")), max(max_gain, Decimal("0"))


def compute_hit_flags(bars: list[PriceBar], recommendation: Recommendation) -> HitFlags:
    """Only meaningful for long (BUY/STRONG_BUY) setups, whose stop sits
    below and targets sit above the entry — the only actions with a
    validated ascending ladder. Other actions report no hits."""
    if recommendation.action not in (Action.STRONG_BUY, Action.BUY) or not bars:
        return HitFlags(False, False, False, False)
    lows = [b.low for b in bars]
    highs = [b.high for b in bars]
    return HitFlags(
        hit_stop_loss=min(lows) <= recommendation.stop_loss,
        hit_tp1=max(highs) >= recommendation.take_profit_1,
        hit_tp2=max(highs) >= recommendation.take_profit_2,
        hit_tp3=max(highs) >= recommendation.take_profit_3,
    )


def compute_accuracy_score(direction_correct: bool, hits: HitFlags) -> float:
    """0.0-1.0. Getting stopped out zeroes the score regardless of
    direction — a thesis that gets stopped out failed, even if price later
    recovered. Otherwise: half credit for direction, partial credit per
    target reached."""
    if hits.hit_stop_loss:
        return 0.0
    score = 0.5 if direction_correct else 0.0
    score += 0.2 if hits.hit_tp1 else 0.0
    score += 0.15 if hits.hit_tp2 else 0.0
    score += 0.15 if hits.hit_tp3 else 0.0
    return min(1.0, score)


def update_rolling_accuracy(previous_metric: dict, new_score: float) -> dict:
    """Simple running mean — no decay. `previous_metric` is whatever was
    stored on the LearningRecord (empty dict if none existed yet)."""
    sample_size = previous_metric.get("sample_size", 0)
    previous_avg = previous_metric.get("rolling_accuracy", 0.0)
    new_sample_size = sample_size + 1
    new_avg = (previous_avg * sample_size + new_score) / new_sample_size
    return {"rolling_accuracy": round(new_avg, 4), "sample_size": new_sample_size}

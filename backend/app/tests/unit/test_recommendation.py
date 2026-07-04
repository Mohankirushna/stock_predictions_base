from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.common.errors import InvariantViolation
from app.domain.common.values import PriceRange
from app.domain.research.recommendation import Action, HoldingPeriod, Recommendation


def make_rec(**overrides) -> Recommendation:
    defaults = dict(
        company_id=uuid4(),
        action=Action.BUY,
        current_price=Decimal("189"),
        entry_zone=PriceRange(Decimal("185"), Decimal("188")),
        stop_loss=Decimal("179"),
        take_profit_1=Decimal("195"),
        take_profit_2=Decimal("204"),
        take_profit_3=Decimal("218"),
        holding_period=HoldingPeriod.MEDIUM,
        confidence=0.72,
        risk_reward=Decimal("2.4"),
        explanation="Strong technicals and improving fundamentals.",
        uncertainty_note="Earnings next week could invalidate the setup.",
        master_score=78.0,
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


def test_valid_recommendation_constructs() -> None:
    rec = make_rec()
    assert rec.action is Action.BUY
    assert rec.master_score == 78.0


def test_certainty_is_forbidden() -> None:
    with pytest.raises(InvariantViolation, match="certainty"):
        make_rec(confidence=1.0)


def test_uncertainty_note_is_required() -> None:
    with pytest.raises(InvariantViolation, match="uncertainty_note"):
        make_rec(uncertainty_note="  ")


def test_explanation_is_required() -> None:
    with pytest.raises(InvariantViolation, match="explanation"):
        make_rec(explanation="")


def test_stop_loss_must_be_below_entry_for_buys() -> None:
    with pytest.raises(InvariantViolation, match="stop loss"):
        make_rec(stop_loss=Decimal("186"))


def test_take_profit_ladder_must_ascend() -> None:
    with pytest.raises(InvariantViolation, match="ladder"):
        make_rec(take_profit_2=Decimal("194"))


def test_ladder_not_enforced_for_hold() -> None:
    # A HOLD carries levels for reference only; the long ladder rule is
    # meaningful just for buy-side guidance.
    rec = make_rec(action=Action.HOLD, take_profit_2=Decimal("194"))
    assert rec.action is Action.HOLD

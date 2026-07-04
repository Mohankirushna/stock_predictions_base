from decimal import Decimal

import pytest

from app.domain.common.errors import InvariantViolation
from app.domain.common.values import Money, Percentage, PriceRange


def test_money_arithmetic_same_currency() -> None:
    assert Money(Decimal("10")) + Money(Decimal("5")) == Money(Decimal("15"))
    assert Money(Decimal("10")) - Money(Decimal("5")) == Money(Decimal("5"))


def test_money_rejects_currency_mismatch() -> None:
    with pytest.raises(InvariantViolation):
        Money(Decimal("1"), "USD") + Money(Decimal("1"), "EUR")


def test_percentage_bounds() -> None:
    Percentage(0.0)
    Percentage(100.0)
    with pytest.raises(InvariantViolation):
        Percentage(100.1)


def test_price_range_ordering_and_contains() -> None:
    zone = PriceRange(Decimal("185"), Decimal("188"))
    assert zone.contains(Decimal("186"))
    assert not zone.contains(Decimal("189"))
    with pytest.raises(InvariantViolation):
        PriceRange(Decimal("188"), Decimal("185"))

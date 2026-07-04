"""Shared value objects. Frozen dataclasses: equality by value, immutable."""
from dataclasses import dataclass
from decimal import Decimal

from app.domain.common.errors import InvariantViolation


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if len(self.currency) != 3:
            raise InvariantViolation(f"invalid currency code: {self.currency!r}")

    def __add__(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def _assert_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise InvariantViolation(f"currency mismatch: {self.currency} vs {other.currency}")


@dataclass(frozen=True)
class Percentage:
    """0.0–100.0 scale (a score of 78 is Percentage(78.0))."""

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 100.0:
            raise InvariantViolation(f"percentage out of range: {self.value}")


@dataclass(frozen=True)
class PriceRange:
    low: Decimal
    high: Decimal

    def __post_init__(self) -> None:
        if self.low <= 0 or self.high <= 0:
            raise InvariantViolation("price range must be positive")
        if self.low > self.high:
            raise InvariantViolation(f"range low {self.low} exceeds high {self.high}")

    def contains(self, price: Decimal) -> bool:
        return self.low <= price <= self.high

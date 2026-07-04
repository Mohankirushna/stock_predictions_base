"""Portfolio aggregate — bookkeeping of user-recorded transactions.
The platform never executes trades; users record what they did elsewhere.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.common.entity import AggregateRoot, Entity
from app.domain.common.errors import InvariantViolation


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(kw_only=True, eq=False)
class Transaction(Entity):
    portfolio_id: UUID
    company_id: UUID
    side: Side
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal("0")
    executed_at: datetime | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise InvariantViolation("quantity must be positive")
        if self.price <= 0:
            raise InvariantViolation("price must be positive")
        if self.fees < 0:
            raise InvariantViolation("fees cannot be negative")


@dataclass(frozen=True)
class Holding:
    """Derived position: net quantity and average cost from transactions."""

    company_id: UUID
    quantity: Decimal
    avg_cost: Decimal

    def market_value(self, price: Decimal) -> Decimal:
        return self.quantity * price

    def unrealized_pnl(self, price: Decimal) -> Decimal:
        return (price - self.avg_cost) * self.quantity


@dataclass(kw_only=True, eq=False)
class Portfolio(AggregateRoot):
    user_id: UUID
    name: str = "Main"
    base_currency: str = "INR"
    cash_balance: Decimal = Decimal("0")
    transactions: list[Transaction] = field(default_factory=list)

    def record_transaction(self, tx: Transaction) -> None:
        if tx.side is Side.SELL:
            held = self.holdings().get(tx.company_id)
            if held is None or held.quantity < tx.quantity:
                raise InvariantViolation("cannot record a sell larger than the held quantity")
        self.transactions.append(tx)
        self.touch()

    def holdings(self) -> dict[UUID, Holding]:
        """Average-cost basis: buys re-average, sells reduce quantity only."""
        qty: dict[UUID, Decimal] = {}
        cost: dict[UUID, Decimal] = {}
        for tx in sorted(self.transactions, key=lambda t: t.executed_at or t.created_at):
            q = qty.get(tx.company_id, Decimal("0"))
            c = cost.get(tx.company_id, Decimal("0"))
            if tx.side is Side.BUY:
                qty[tx.company_id] = q + tx.quantity
                cost[tx.company_id] = c + tx.quantity * tx.price + tx.fees
            else:
                if q > 0:
                    cost[tx.company_id] = c * (q - tx.quantity) / q
                qty[tx.company_id] = q - tx.quantity
        return {
            cid: Holding(company_id=cid, quantity=q, avg_cost=(cost[cid] / q).quantize(Decimal("0.0001")))
            for cid, q in qty.items()
            if q > 0
        }

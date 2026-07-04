from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.common.errors import InvariantViolation
from app.domain.portfolio.portfolio import Portfolio, Side, Transaction
from app.domain.portfolio.watchlist import Watchlist


def tx(portfolio_id, company_id, side, qty, price) -> Transaction:
    return Transaction(
        portfolio_id=portfolio_id,
        company_id=company_id,
        side=side,
        quantity=Decimal(qty),
        price=Decimal(price),
    )


def test_holdings_average_cost() -> None:
    p = Portfolio(user_id=uuid4())
    aapl = uuid4()
    p.record_transaction(tx(p.id, aapl, Side.BUY, "10", "100"))
    p.record_transaction(tx(p.id, aapl, Side.BUY, "10", "200"))
    holding = p.holdings()[aapl]
    assert holding.quantity == Decimal("20")
    assert holding.avg_cost == Decimal("150.0000")


def test_sell_reduces_quantity_keeps_avg_cost() -> None:
    p = Portfolio(user_id=uuid4())
    aapl = uuid4()
    p.record_transaction(tx(p.id, aapl, Side.BUY, "20", "150"))
    p.record_transaction(tx(p.id, aapl, Side.SELL, "10", "180"))
    holding = p.holdings()[aapl]
    assert holding.quantity == Decimal("10")
    assert holding.avg_cost == Decimal("150.0000")


def test_cannot_oversell() -> None:
    p = Portfolio(user_id=uuid4())
    aapl = uuid4()
    p.record_transaction(tx(p.id, aapl, Side.BUY, "5", "100"))
    with pytest.raises(InvariantViolation, match="sell larger"):
        p.record_transaction(tx(p.id, aapl, Side.SELL, "6", "100"))


def test_unrealized_pnl() -> None:
    p = Portfolio(user_id=uuid4())
    aapl = uuid4()
    p.record_transaction(tx(p.id, aapl, Side.BUY, "10", "100"))
    holding = p.holdings()[aapl]
    assert holding.unrealized_pnl(Decimal("120")) == Decimal("200.0000")


def test_watchlist_rejects_duplicates() -> None:
    w = Watchlist(user_id=uuid4())
    company = uuid4()
    w.add(company)
    with pytest.raises(InvariantViolation, match="already"):
        w.add(company)


def test_watchlist_remove_missing_raises() -> None:
    w = Watchlist(user_id=uuid4())
    with pytest.raises(InvariantViolation, match="not on"):
        w.remove(uuid4())

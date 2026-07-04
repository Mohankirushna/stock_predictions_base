"""Portfolio endpoints — user-owned, auth required. Transactions are
bookkeeping only: the platform never places or executes a trade."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_uow
from app.api.v1.envelope import ok
from app.api.v1.schemas.portfolio import (
    CreatePortfolioRequest,
    CreateTransactionRequest,
    PortfolioAnalyticsOut,
    PortfolioOut,
    UpdatePortfolioRequest,
)
from app.core.container import container
from app.core.errors import NotFoundError
from app.domain.identity.user import User
from app.domain.portfolio.portfolio import Portfolio, Side, Transaction
from app.domain.ports.unit_of_work import UnitOfWork

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


async def _get_owned(uow: UnitOfWork, portfolio_id: UUID, user: User) -> Portfolio:
    portfolio = await uow.portfolios.get(portfolio_id)
    if portfolio is None or portfolio.user_id != user.id:
        raise NotFoundError("portfolio not found")
    return portfolio


@router.get("")
async def list_portfolios(
    user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    portfolios = await uow.portfolios.for_user(user.id)
    return ok([PortfolioOut.from_domain(p) for p in portfolios])


@router.post("", status_code=201)
async def create_portfolio(
    body: CreatePortfolioRequest, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    portfolio = Portfolio(user_id=user.id, name=body.name, base_currency=body.base_currency)
    await uow.portfolios.add(portfolio)
    await uow.commit()
    return ok(PortfolioOut.from_domain(portfolio))


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: UUID, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    return ok(PortfolioOut.from_domain(await _get_owned(uow, portfolio_id, user)))


@router.patch("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: UUID, body: UpdatePortfolioRequest,
    user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    portfolio = await _get_owned(uow, portfolio_id, user)
    if body.name is not None:
        portfolio.name = body.name
        portfolio.touch()
    await uow.portfolios.update(portfolio)
    await uow.commit()
    return ok(PortfolioOut.from_domain(portfolio))


@router.delete("/{portfolio_id}", status_code=204)
async def delete_portfolio(
    portfolio_id: UUID, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> None:
    await _get_owned(uow, portfolio_id, user)
    await uow.portfolios.delete(portfolio_id)
    await uow.commit()


@router.post("/{portfolio_id}/transactions", status_code=201)
async def record_transaction(
    portfolio_id: UUID, body: CreateTransactionRequest,
    user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    portfolio = await _get_owned(uow, portfolio_id, user)
    company = await uow.companies.get_by_symbol(body.symbol.upper())
    if company is None:
        raise NotFoundError(f"no company found for symbol {body.symbol.upper()!r}")

    transaction = Transaction(
        portfolio_id=portfolio.id, company_id=company.id, side=Side(body.side),
        quantity=body.quantity, price=body.price, fees=body.fees,
        executed_at=body.executed_at, note=body.note,
    )
    portfolio.record_transaction(transaction)
    await uow.portfolios.update(portfolio)
    await uow.commit()
    return ok(PortfolioOut.from_domain(portfolio))


@router.get("/{portfolio_id}/analytics")
async def get_portfolio_analytics(
    portfolio_id: UUID, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    from app.application.agents.portfolio.agent import PortfolioAgent

    await _get_owned(uow, portfolio_id, user)  # ownership check before running the agent
    result = await container.resolve(PortfolioAgent).run(portfolio_id=portfolio_id)
    if not result.success:
        raise NotFoundError(result.error or "unable to compute analytics")
    return ok(PortfolioAnalyticsOut(**result.summary))

"""Agent 9 — Portfolio. Computed synchronously per request (portfolio
analytics must reflect the latest transaction, not a stale scheduled
snapshot), but still framed as an agent — `run()` gives it the same
tracing/error-isolation as every other agent, and nothing prevents an
agent from being called directly from a route handler.
"""
from collections.abc import Callable
from typing import Any

from app.application.agents.base import AgentBase
from app.application.agents.portfolio import analytics as an
from app.domain.market.price import PriceInterval
from app.domain.ports.unit_of_work import UnitOfWork


class PortfolioAgent(AgentBase):
    name = "portfolio"

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        super().__init__()
        self._uow_factory = uow_factory

    async def _execute(self, portfolio_id) -> dict[str, Any]:
        async with self._uow_factory() as uow:
            portfolio = await uow.portfolios.get(portfolio_id)
            if portfolio is None:
                raise ValueError(f"no portfolio found for id {portfolio_id}")

            holding_views = []
            for company_id, holding in portfolio.holdings().items():
                company = await uow.companies.get(company_id)
                if company is None:
                    continue
                bar = await uow.prices.latest_bar(company_id, PriceInterval.D1)
                price = bar.close if bar else holding.avg_cost  # fall back to cost basis if unpriced
                holding_views.append(
                    an.HoldingView(
                        symbol=company.symbol, sector=company.sector,
                        quantity=holding.quantity, avg_cost=holding.avg_cost, price=price,
                    )
                )

        total = an.total_value(holding_views, portfolio.cash_balance)
        pnl = an.total_unrealized_pnl(holding_views)
        allocation = an.allocation_pct(holding_views, total)
        sectors = an.sector_exposure_pct(holding_views, total)
        diversification = an.diversification_score(allocation)
        risk = an.risk_score(sectors, diversification)
        pnl_pct = float(pnl / (total - pnl) * 100) if (total - pnl) > 0 else 0.0

        return {
            "total_value": str(total),
            "cash_balance": str(portfolio.cash_balance),
            "unrealized_pnl": str(pnl),
            "unrealized_pnl_pct": round(pnl_pct, 2),
            "allocation_pct": {k: round(v, 2) for k, v in allocation.items()},
            "sector_exposure_pct": {k: round(v, 2) for k, v in sectors.items()},
            "diversification_score": diversification,
            "risk_score": risk,
            "health_grade": an.health_grade(risk, diversification, pnl_pct),
            "rebalancing_suggestions": an.rebalancing_suggestions(allocation, sectors),
            "holdings": [
                {
                    "symbol": h.symbol, "sector": h.sector, "quantity": str(h.quantity),
                    "avg_cost": str(h.avg_cost), "price": str(h.price),
                    "market_value": str(h.market_value), "unrealized_pnl": str(h.unrealized_pnl),
                    "unrealized_pnl_pct": round(h.unrealized_pnl_pct, 2),
                }
                for h in holding_views
            ],
        }

"""Agent 4 — Fundamental Analysis. Pure Python, no AI: fetches each
company's raw vendor metrics and computes/normalizes them into a
structured FundamentalSnapshot (ratios, growth, margins, dividends).

Absolute financial-statement figures (revenue, net income, free cash flow
in dollars) are only populated when the vendor's basic-financials endpoint
happens to expose them directly — full line-item statement parsing is a
heavier data source out of scope for this agent.
"""
from collections.abc import Callable
from datetime import date
from typing import Any

from app.application.agents.base import AgentBase
from app.application.agents.fundamental_analysis.ratios import build_fundamental_fields
from app.domain.intelligence.fundamentals import FundamentalSnapshot, Period
from app.domain.ports.market_data_source import MarketDataSource
from app.domain.ports.unit_of_work import UnitOfWork


class FundamentalAnalysisAgent(AgentBase):
    name = "fundamental_analysis"

    def __init__(self, uow_factory: Callable[[], UnitOfWork], market_data: MarketDataSource) -> None:
        super().__init__()
        self._uow_factory = uow_factory
        self._market_data = market_data

    async def _execute(self, symbols: list[str]) -> dict[str, Any]:
        computed, skipped = 0, []
        async with self._uow_factory() as uow:
            for symbol in symbols:
                company = await uow.companies.get_by_symbol(symbol)
                if company is None:
                    skipped.append(symbol)
                    continue

                raw = await self._market_data.get_fundamentals_raw(symbol)
                if not raw:
                    skipped.append(symbol)
                    continue

                snapshot = FundamentalSnapshot(
                    company_id=company.id, period=Period.TTM, fiscal_date=date.today(),
                    **build_fundamental_fields(raw),
                )
                await uow.fundamentals.save(snapshot)
                computed += 1
            await uow.commit()

        return {"computed": computed, "skipped": skipped}

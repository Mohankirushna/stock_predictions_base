"""Fundamental analysis domain objects — produced by the pure-Python
Fundamental Analysis Agent (no AI involved)."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class Period(StrEnum):
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    TTM = "ttm"


@dataclass(kw_only=True)
class FundamentalSnapshot:
    company_id: UUID
    period: Period
    fiscal_date: date

    revenue: Decimal | None = None
    revenue_growth_yoy: Decimal | None = None
    net_income: Decimal | None = None
    eps: Decimal | None = None
    eps_growth_yoy: Decimal | None = None

    total_debt: Decimal | None = None
    debt_to_equity: Decimal | None = None
    free_cash_flow: Decimal | None = None
    operating_cash_flow: Decimal | None = None

    roe: Decimal | None = None
    roa: Decimal | None = None
    pe: Decimal | None = None
    peg: Decimal | None = None
    gross_margin: Decimal | None = None
    operating_margin: Decimal | None = None
    net_margin: Decimal | None = None

    institutional_ownership_pct: Decimal | None = None
    dividend_yield: Decimal | None = None
    dividend_payout_ratio: Decimal | None = None

    @property
    def is_profitable(self) -> bool | None:
        return None if self.net_income is None else self.net_income > 0

    @property
    def has_healthy_leverage(self) -> bool | None:
        """Rule of thumb: D/E under 2 is manageable for most sectors."""
        return None if self.debt_to_equity is None else self.debt_to_equity < 2

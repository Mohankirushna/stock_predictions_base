from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.common.entity import AggregateRoot
from app.domain.common.errors import InvariantViolation


@dataclass(kw_only=True, eq=False)
class Company(AggregateRoot):
    symbol: str
    name: str
    exchange: str = ""
    sector: str = ""
    industry: str = ""
    country: str = ""
    currency: str = "USD"
    market_cap: Decimal | None = None
    logo_url: str = ""
    description: str = ""
    is_active: bool = True
    last_synced_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.isascii():
            raise InvariantViolation(f"invalid symbol: {self.symbol!r}")
        self.symbol = self.symbol.upper()

    def mark_synced(self, at: datetime) -> None:
        self.last_synced_at = at
        self.touch()

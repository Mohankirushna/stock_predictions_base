from dataclasses import dataclass, field
from uuid import UUID

from app.domain.common.entity import AggregateRoot, Entity
from app.domain.common.errors import InvariantViolation


@dataclass(kw_only=True, eq=False)
class WatchlistItem(Entity):
    watchlist_id: UUID
    company_id: UUID
    note: str = ""


@dataclass(kw_only=True, eq=False)
class Watchlist(AggregateRoot):
    user_id: UUID
    name: str = "Default"
    is_default: bool = False
    items: list[WatchlistItem] = field(default_factory=list)

    MAX_ITEMS = 200  # keeps per-user refresh jobs bounded

    def add(self, company_id: UUID, note: str = "") -> WatchlistItem:
        if any(i.company_id == company_id for i in self.items):
            raise InvariantViolation("company already on this watchlist")
        if len(self.items) >= self.MAX_ITEMS:
            raise InvariantViolation(f"watchlist limit of {self.MAX_ITEMS} reached")
        item = WatchlistItem(watchlist_id=self.id, company_id=company_id, note=note)
        self.items.append(item)
        self.touch()
        return item

    def remove(self, company_id: UUID) -> None:
        before = len(self.items)
        self.items = [i for i in self.items if i.company_id != company_id]
        if len(self.items) == before:
            raise InvariantViolation("company not on this watchlist")
        self.touch()

    def company_ids(self) -> list[UUID]:
        return [i.company_id for i in self.items]

"""Entity and AggregateRoot base classes.

Domain layer rule: stdlib only — no pydantic, no SQLAlchemy, no framework code.
Entities compare by identity; value objects (frozen dataclasses) by value.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.common.events import DomainEvent


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(kw_only=True)
class Entity:
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and other.id == self.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))

    def touch(self) -> None:
        self.updated_at = utc_now()


@dataclass(kw_only=True, eq=False)
class AggregateRoot(Entity):
    """Aggregate roots collect domain events; the unit of work drains and
    dispatches them after a successful commit."""

    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    def record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events

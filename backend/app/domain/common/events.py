"""Domain events — facts that already happened, named in past tense."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def name(self) -> str:
        return type(self).__name__

    def payload(self) -> dict[str, Any]:
        """Serializable view for the event bus; subclasses may extend."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

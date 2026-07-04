"""Records AI spend/usage per call — backs the ai_usage_log table for admin
spend dashboards. Deliberately not part of the UnitOfWork: usage should be
recorded even if the calling business transaction rolls back."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class UsageRecord:
    provider: str
    model: str
    agent: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: datetime | None = field(default=None)  # populated on read, ignored on write


class UsageRecorder(Protocol):
    async def record(self, usage: UsageRecord) -> None: ...

    async def list_recent(
        self, provider: str | None, since: datetime | None, limit: int
    ) -> list[UsageRecord]:
        """Admin usage log — most recent first."""
        ...

    async def total_cost(self, provider: str | None, since: datetime | None) -> float:
        ...

"""Shared agent lifecycle: timing, logging, and a uniform result envelope.

Concrete agents implement `_execute()`; `run()` wraps it with tracing and a
consistent error policy so one failing agent never crashes the scheduler —
Celery tasks (M9) call `run()` and inspect `AgentResult.success` rather than
letting exceptions propagate.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger


@dataclass
class AgentResult:
    agent: str
    started_at: datetime
    finished_at: datetime
    success: bool
    summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def duration_ms(self) -> int:
        return int((self.finished_at - self.started_at).total_seconds() * 1000)


class AgentBase(ABC):
    name: str

    def __init__(self) -> None:
        self._logger = get_logger(f"agent.{self.name}")

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Do the work; return a JSON-serializable summary."""
        ...

    async def run(self, **kwargs: Any) -> AgentResult:
        started = datetime.now(UTC)
        self._logger.info("agent started", extra={"ctx": {"agent": self.name}})
        try:
            summary = await self._execute(**kwargs)
        except Exception as exc:  # noqa: BLE001 — isolate failure to this agent's result
            finished = datetime.now(UTC)
            self._logger.error("agent failed", extra={"ctx": {"agent": self.name, "error": str(exc)}})
            return AgentResult(self.name, started, finished, False, error=str(exc))

        finished = datetime.now(UTC)
        result = AgentResult(self.name, started, finished, True, summary)
        self._logger.info(
            "agent finished",
            extra={"ctx": {"agent": self.name, "duration_ms": result.duration_ms, "summary": summary}},
        )
        return result

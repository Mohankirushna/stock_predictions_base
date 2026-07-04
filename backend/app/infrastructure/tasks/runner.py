"""Shared task-runner helper: resolve target symbols if none were given,
run an agent, and shape the AgentResult into a plain JSON-serializable
dict (Celery task return values must be JSON-serializable)."""
from typing import Any, Protocol

from app.core.config import Settings
from app.core.container import container
from app.domain.ports.unit_of_work import UnitOfWork
from app.infrastructure.tasks.symbols import target_symbols


class RunnableAgent(Protocol):
    async def run(self, **kwargs: Any) -> Any: ...


async def run_agent_task(agent: RunnableAgent, symbols: list[str] | None, **kwargs: Any) -> dict[str, Any]:
    if symbols is None:
        async with container.resolve(UnitOfWork) as uow:
            symbols = await target_symbols(uow, container.resolve(Settings))
    result = await agent.run(symbols=symbols, **kwargs)
    return {"agent": result.agent, "success": result.success, "summary": result.summary, "error": result.error}

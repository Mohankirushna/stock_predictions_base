from typing import Any

from app.application.agents.base import AgentBase


class SucceedingAgent(AgentBase):
    name = "succeeding"

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        return {"processed": kwargs.get("count", 0)}


class FailingAgent(AgentBase):
    name = "failing"

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("vendor is down")


async def test_successful_run_returns_summary() -> None:
    result = await SucceedingAgent().run(count=5)
    assert result.success is True
    assert result.summary == {"processed": 5}
    assert result.error is None
    assert result.duration_ms >= 0


async def test_failed_run_is_isolated_not_raised() -> None:
    result = await FailingAgent().run()
    assert result.success is False
    assert result.error == "vendor is down"
    assert result.summary == {}


async def test_result_records_agent_name_and_timestamps() -> None:
    result = await SucceedingAgent().run()
    assert result.agent == "succeeding"
    assert result.finished_at >= result.started_at

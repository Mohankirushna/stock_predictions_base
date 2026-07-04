"""SQL usage recorder — writes each AI call to ai_usage_log for spend
dashboards. Uses its own short-lived session rather than the caller's
UnitOfWork, so a usage record survives even if the calling business
transaction later rolls back."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.ports.usage_recorder import UsageRecord
from app.infrastructure.db.models.learning import AIUsageLogModel


class SqlUsageRecorder:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def record(self, usage: UsageRecord) -> None:
        async with self._session_factory() as session:
            session.add(
                AIUsageLogModel(
                    provider=usage.provider, model=usage.model, agent=usage.agent,
                    tokens_in=usage.tokens_in, tokens_out=usage.tokens_out, cost_usd=usage.cost_usd,
                )
            )
            await session.commit()

    async def list_recent(
        self, provider: str | None, since: datetime | None, limit: int
    ) -> list[UsageRecord]:
        async with self._session_factory() as session:
            stmt = select(AIUsageLogModel)
            if provider:
                stmt = stmt.where(AIUsageLogModel.provider == provider)
            if since:
                stmt = stmt.where(AIUsageLogModel.created_at >= since)
            rows = await session.scalars(stmt.order_by(AIUsageLogModel.created_at.desc()).limit(limit))
            return [
                UsageRecord(
                    provider=m.provider, model=m.model, agent=m.agent, tokens_in=m.tokens_in,
                    tokens_out=m.tokens_out, cost_usd=m.cost_usd, created_at=m.created_at,
                )
                for m in rows
            ]

    async def total_cost(self, provider: str | None, since: datetime | None) -> float:
        async with self._session_factory() as session:
            stmt = select(func.coalesce(func.sum(AIUsageLogModel.cost_usd), 0.0))
            if provider:
                stmt = stmt.where(AIUsageLogModel.provider == provider)
            if since:
                stmt = stmt.where(AIUsageLogModel.created_at >= since)
            return float(await session.scalar(stmt) or 0.0)

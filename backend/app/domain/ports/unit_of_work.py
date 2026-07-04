"""Unit-of-work port: one atomic transaction spanning multiple repositories,
draining aggregate events for dispatch after a successful commit."""
from types import TracebackType
from typing import Protocol

from app.domain.ports import repositories as r


class UnitOfWork(Protocol):
    users: r.UserRepository
    companies: r.CompanyRepository
    prices: r.PriceRepository
    news: r.NewsRepository
    technicals: r.TechnicalsRepository
    fundamentals: r.FundamentalsRepository
    market_events: r.MarketEventRepository
    recommendations: r.RecommendationRepository
    research_reports: r.ResearchReportRepository
    ai_reasoning: r.AIReasoningRepository
    predictions: r.PredictionRepository
    learning: r.LearningRepository
    portfolios: r.PortfolioRepository
    watchlists: r.WatchlistRepository
    alerts: r.AlertRepository
    notifications: r.NotificationRepository

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def flush(self) -> None:
        """Resolves pending inserts against the DB (assigning FKs) without
        committing — needed whenever a use case adds a parent, then a child
        referencing it, within the same transaction (SQLAlchemy doesn't
        auto-order inserts across unrelated mapped classes)."""
        ...

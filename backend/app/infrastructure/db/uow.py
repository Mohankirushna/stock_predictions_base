"""SQLAlchemy Unit of Work — one session/transaction across all repositories.

Usage:
    async with uow_factory() as uow:
        user = await uow.users.get_by_email(email)
        ...
        await uow.commit()

Exiting without commit rolls back, so partial writes never leak.
"""
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.repositories.alerting_repo import (
    SqlAlertRepository,
    SqlNotificationRepository,
)
from app.infrastructure.repositories.identity_repo import SqlUserRepository
from app.infrastructure.repositories.intelligence_repo import (
    SqlFundamentalsRepository,
    SqlNewsRepository,
    SqlTechnicalsRepository,
)
from app.infrastructure.repositories.learning_repo import SqlLearningRepository
from app.infrastructure.repositories.market_repo import (
    SqlCompanyRepository,
    SqlMarketEventRepository,
    SqlPriceRepository,
)
from app.infrastructure.repositories.portfolio_repo import (
    SqlPortfolioRepository,
    SqlWatchlistRepository,
)
from app.infrastructure.repositories.research_repo import (
    SqlAIReasoningRepository,
    SqlPredictionRepository,
    SqlRecommendationRepository,
    SqlResearchReportRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        s = self._session
        self.users = SqlUserRepository(s)
        self.companies = SqlCompanyRepository(s)
        self.prices = SqlPriceRepository(s)
        self.market_events = SqlMarketEventRepository(s)
        self.news = SqlNewsRepository(s)
        self.technicals = SqlTechnicalsRepository(s)
        self.fundamentals = SqlFundamentalsRepository(s)
        self.recommendations = SqlRecommendationRepository(s)
        self.research_reports = SqlResearchReportRepository(s)
        self.ai_reasoning = SqlAIReasoningRepository(s)
        self.predictions = SqlPredictionRepository(s)
        self.learning = SqlLearningRepository(s)
        self.portfolios = SqlPortfolioRepository(s)
        self.watchlists = SqlWatchlistRepository(s)
        self.alerts = SqlAlertRepository(s)
        self.notifications = SqlNotificationRepository(s)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None, "commit outside of context"
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None, "rollback outside of context"
        await self._session.rollback()

    async def flush(self) -> None:
        assert self._session is not None, "flush outside of context"
        await self._session.flush()

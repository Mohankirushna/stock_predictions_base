"""Lightweight dependency-injection container.

Ports (interfaces in app/domain/ports) are bound to concrete adapters here,
and only here — application code resolves by port type and never imports
infrastructure directly.

Usage:
    container.register(AIProvider, lambda c: build_ai_router(c.resolve(Settings)))
    provider = container.resolve(AIProvider)

Bindings are lazy singletons by default; use singleton=False for per-resolve
instances (e.g. unit-of-work).
"""
from collections.abc import Callable
from threading import Lock
from typing import Any, TypeVar

T = TypeVar("T")

Provider = Callable[["Container"], Any]


class ContainerError(RuntimeError):
    pass


class Container:
    def __init__(self) -> None:
        self._providers: dict[type, tuple[Provider, bool]] = {}
        self._singletons: dict[type, Any] = {}
        self._lock = Lock()

    def register(self, key: type[T], provider: Provider, *, singleton: bool = True) -> None:
        with self._lock:
            self._providers[key] = (provider, singleton)
            self._singletons.pop(key, None)

    def register_instance(self, key: type[T], instance: T) -> None:
        self.register(key, lambda _: instance)

    def resolve(self, key: type[T]) -> T:
        if key in self._singletons:
            return self._singletons[key]
        try:
            provider, singleton = self._providers[key]
        except KeyError:
            raise ContainerError(f"No binding registered for {key.__name__}") from None
        instance = provider(self)
        if singleton:
            with self._lock:
                self._singletons.setdefault(key, instance)
                instance = self._singletons[key]
        return instance

    def is_registered(self, key: type) -> bool:
        return key in self._providers

    def reset(self) -> None:
        """Clear cached singletons — used between tests."""
        with self._lock:
            self._singletons.clear()


container = Container()


def wire(settings: Any) -> Container:
    """Bind all ports to adapters. Later modules (db, ai, cache, …) extend this.

    Called once from the app factory and from the Celery worker bootstrap so
    both processes share identical wiring.
    """
    from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

    from app.application.agents.alert.agent import AlertAgent
    from app.application.agents.data_collection.agent import DataCollectionAgent
    from app.application.agents.fundamental_analysis.agent import FundamentalAnalysisAgent
    from app.application.agents.learning.agent import LearningAgent
    from app.application.agents.market_intelligence.agent import MarketIntelligenceAgent
    from app.application.agents.news_intelligence.agent import NewsIntelligenceAgent
    from app.application.agents.opportunity.agent import OpportunityDiscoveryAgent
    from app.application.agents.portfolio.agent import PortfolioAgent
    from app.application.agents.recommendation.agent import RecommendationAgent
    from app.application.agents.research.agent import ResearchAgent
    from app.application.agents.technical_analysis.agent import TechnicalAnalysisAgent
    from app.application.services.token_service import TokenService
    from app.core.config import Settings
    from app.domain.ports.ai_provider import AIProvider
    from app.domain.ports.cache import Cache
    from app.domain.ports.market_data_source import MarketDataSource
    from app.domain.ports.token_store import TokenRevocationStore
    from app.domain.ports.unit_of_work import UnitOfWork
    from app.domain.ports.usage_recorder import UsageRecorder
    from app.domain.ports.vector_store import VectorStore
    from app.infrastructure.ai.router import AIProviderRouter
    from app.infrastructure.ai.usage_log import SqlUsageRecorder
    from app.infrastructure.auth.google_oauth import GoogleOAuthClient
    from app.infrastructure.auth.redis_revocation_store import RedisRevocationStore
    from app.infrastructure.cache.redis_cache import RedisCache
    from app.infrastructure.db.engine import build_engine, build_session_factory
    from app.infrastructure.db.uow import SqlAlchemyUnitOfWork
    from app.infrastructure.market_data.composite import CompositeMarketDataSource
    from app.infrastructure.market_data.marketaux import MarketauxNewsSource
    from app.infrastructure.market_data.registry import build_market_data_source
    from app.infrastructure.vector.qdrant_store import QdrantVectorStore

    container.register_instance(Settings, settings)
    container.register(AsyncEngine, lambda c: build_engine(c.resolve(Settings)))
    container.register(async_sessionmaker, lambda c: build_session_factory(c.resolve(AsyncEngine)))
    container.register(
        UnitOfWork,
        lambda c: SqlAlchemyUnitOfWork(c.resolve(async_sessionmaker)),
        singleton=False,
    )
    # Redis-backed so revocation is shared across horizontally-scaled API nodes.
    container.register(TokenRevocationStore, lambda c: RedisRevocationStore(c.resolve(Settings).redis.url))
    container.register(Cache, lambda c: RedisCache(c.resolve(Settings).redis.url))
    container.register(
        TokenService, lambda c: TokenService(c.resolve(Settings), c.resolve(TokenRevocationStore))
    )
    container.register(GoogleOAuthClient, lambda c: GoogleOAuthClient(c.resolve(Settings).auth))
    container.register(UsageRecorder, lambda c: SqlUsageRecorder(c.resolve(async_sessionmaker)))
    container.register(
        AIProvider, lambda c: AIProviderRouter(c.resolve(Settings), c.resolve(UsageRecorder))
    )

    def _build_market_data_source(c: Container) -> object:
        market = c.resolve(Settings).market
        primary = build_market_data_source(market.provider, market)
        if not market.marketaux_api_key:
            return primary
        return CompositeMarketDataSource(
            primary,
            news_source=MarketauxNewsSource(market.marketaux_api_key),
            cache=c.resolve(Cache),
            news_min_interval_hours=market.marketaux_min_interval_hours,
        )

    container.register(MarketDataSource, _build_market_data_source)
    container.register(
        DataCollectionAgent,
        lambda c: DataCollectionAgent(
            lambda: c.resolve(UnitOfWork), c.resolve(MarketDataSource), c.resolve(Cache)
        ),
    )
    container.register(
        TechnicalAnalysisAgent, lambda c: TechnicalAnalysisAgent(lambda: c.resolve(UnitOfWork))
    )
    container.register(
        FundamentalAnalysisAgent,
        lambda c: FundamentalAnalysisAgent(lambda: c.resolve(UnitOfWork), c.resolve(MarketDataSource)),
    )
    container.register(
        VectorStore,
        lambda c: QdrantVectorStore(c.resolve(Settings).qdrant.url, c.resolve(Settings).qdrant.api_key),
    )
    container.register(
        NewsIntelligenceAgent,
        lambda c: NewsIntelligenceAgent(
            lambda: c.resolve(UnitOfWork), c.resolve(AIProvider), c.resolve(VectorStore)
        ),
    )
    container.register(
        MarketIntelligenceAgent,
        lambda c: MarketIntelligenceAgent(
            lambda: c.resolve(UnitOfWork), c.resolve(MarketDataSource),
            c.resolve(AIProvider), c.resolve(Cache),
        ),
    )
    container.register(
        ResearchAgent,
        lambda c: ResearchAgent(
            lambda: c.resolve(UnitOfWork), c.resolve(AIProvider),
            c.resolve(VectorStore), c.resolve(Cache),
        ),
    )
    container.register(
        OpportunityDiscoveryAgent,
        lambda c: OpportunityDiscoveryAgent(
            lambda: c.resolve(UnitOfWork), c.resolve(AIProvider), c.resolve(Cache)
        ),
    )
    container.register(
        RecommendationAgent,
        lambda c: RecommendationAgent(
            lambda: c.resolve(UnitOfWork), c.resolve(MarketDataSource),
            c.resolve(AIProvider), c.resolve(Cache),
        ),
    )
    container.register(PortfolioAgent, lambda c: PortfolioAgent(lambda: c.resolve(UnitOfWork)))
    container.register(
        AlertAgent,
        lambda c: AlertAgent(lambda: c.resolve(UnitOfWork), c.resolve(MarketDataSource), c.resolve(Cache)),
    )
    container.register(LearningAgent, lambda c: LearningAgent(lambda: c.resolve(UnitOfWork)))
    return container

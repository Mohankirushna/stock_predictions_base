"""Confirms app.core.container.wire() binds every port introduced so far to
a concrete adapter — catches missing/broken registrations at test time
rather than at first request."""
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

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
from app.core.container import container, wire
from app.core.errors import ExternalServiceError
from app.domain.ports.ai_provider import AIProvider
from app.domain.ports.cache import Cache
from app.domain.ports.market_data_source import MarketDataSource
from app.domain.ports.token_store import TokenRevocationStore
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usage_recorder import UsageRecorder
from app.domain.ports.vector_store import VectorStore
from app.infrastructure.ai.router import AIProviderRouter
from app.infrastructure.auth.redis_revocation_store import RedisRevocationStore
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from app.infrastructure.market_data.composite import CompositeMarketDataSource
from app.infrastructure.market_data.finnhub import FinnhubMarketDataSource
from app.infrastructure.vector.qdrant_store import QdrantVectorStore


def test_wire_binds_all_expected_ports() -> None:
    wire(Settings(app_secret_key="x" * 32))

    assert isinstance(container.resolve(UnitOfWork), SqlAlchemyUnitOfWork)
    assert isinstance(container.resolve(TokenRevocationStore), RedisRevocationStore)
    assert isinstance(container.resolve(Cache), RedisCache)
    assert isinstance(container.resolve(TokenService), TokenService)
    assert isinstance(container.resolve(AIProvider), AIProviderRouter)
    assert container.is_registered(UsageRecorder)
    assert container.is_registered(async_sessionmaker)
    assert container.is_registered(MarketDataSource)
    assert container.is_registered(DataCollectionAgent)
    assert isinstance(container.resolve(TechnicalAnalysisAgent), TechnicalAnalysisAgent)
    # FundamentalAnalysisAgent needs MarketDataSource (needs a Finnhub key) to
    # resolve — checked for registration only here; resolved with a key below.
    assert container.is_registered(FundamentalAnalysisAgent)
    assert isinstance(container.resolve(VectorStore), QdrantVectorStore)
    assert isinstance(container.resolve(NewsIntelligenceAgent), NewsIntelligenceAgent)
    assert container.is_registered(MarketIntelligenceAgent)  # resolves with a Finnhub key below
    assert isinstance(container.resolve(ResearchAgent), ResearchAgent)
    assert isinstance(container.resolve(OpportunityDiscoveryAgent), OpportunityDiscoveryAgent)
    assert isinstance(container.resolve(PortfolioAgent), PortfolioAgent)
    assert container.is_registered(AlertAgent)  # resolves with a Finnhub key below
    assert container.is_registered(RecommendationAgent)  # resolves with a Finnhub key below


def test_ai_provider_is_a_process_wide_singleton() -> None:
    wire(Settings(app_secret_key="x" * 32))
    assert container.resolve(AIProvider) is container.resolve(AIProvider)


def test_market_data_source_resolves_once_key_is_configured() -> None:
    # Explicit provider/marketaux_api_key so this test's expectations don't
    # depend on whichever provider happens to be set in .env on this machine.
    wire(
        Settings(
            app_secret_key="x" * 32,
            market={"provider": "finnhub", "finnhub_api_key": "test-key", "marketaux_api_key": ""},
        )
    )
    assert isinstance(container.resolve(MarketDataSource), FinnhubMarketDataSource)
    assert isinstance(container.resolve(DataCollectionAgent), DataCollectionAgent)
    assert isinstance(container.resolve(FundamentalAnalysisAgent), FundamentalAnalysisAgent)
    assert isinstance(container.resolve(RecommendationAgent), RecommendationAgent)
    assert isinstance(container.resolve(AlertAgent), AlertAgent)
    assert isinstance(container.resolve(LearningAgent), LearningAgent)
    assert isinstance(container.resolve(MarketIntelligenceAgent), MarketIntelligenceAgent)


def test_market_data_source_without_key_raises_on_resolve() -> None:
    wire(Settings(app_secret_key="x" * 32, market={"provider": "finnhub", "finnhub_api_key": ""}))
    with pytest.raises(ExternalServiceError, match="missing API key"):
        container.resolve(MarketDataSource)


def test_market_data_source_wraps_with_composite_when_marketaux_key_present() -> None:
    wire(
        Settings(
            app_secret_key="x" * 32,
            market={"provider": "finnhub", "finnhub_api_key": "test-key", "marketaux_api_key": "news-key"},
        )
    )
    source = container.resolve(MarketDataSource)
    assert isinstance(source, CompositeMarketDataSource)

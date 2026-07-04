"""Import every model so Base.metadata sees the full schema (Alembic autogenerate)."""
from app.infrastructure.db.models.alerting import AlertModel, NotificationModel
from app.infrastructure.db.models.identity import UserModel
from app.infrastructure.db.models.intelligence import (
    FundamentalsModel,
    IndicatorModel,
    NewsModel,
    TechnicalsModel,
)
from app.infrastructure.db.models.learning import (
    AIUsageLogModel,
    LearningDataModel,
    PredictionHistoryModel,
)
from app.infrastructure.db.models.market import (
    CompanyModel,
    HistoricalPriceModel,
    MarketEventModel,
)
from app.infrastructure.db.models.portfolio import (
    PortfolioModel,
    PortfolioTransactionModel,
    WatchlistItemModel,
    WatchlistModel,
)
from app.infrastructure.db.models.research import (
    AIReasoningModel,
    PredictionModel,
    RecommendationModel,
    ResearchReportModel,
)

__all__ = [
    "AIReasoningModel",
    "AIUsageLogModel",
    "AlertModel",
    "CompanyModel",
    "FundamentalsModel",
    "HistoricalPriceModel",
    "IndicatorModel",
    "LearningDataModel",
    "MarketEventModel",
    "NewsModel",
    "NotificationModel",
    "PortfolioModel",
    "PortfolioTransactionModel",
    "PredictionHistoryModel",
    "PredictionModel",
    "RecommendationModel",
    "ResearchReportModel",
    "TechnicalsModel",
    "UserModel",
    "WatchlistItemModel",
    "WatchlistModel",
]

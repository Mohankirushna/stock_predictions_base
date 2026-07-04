from datetime import datetime

from pydantic import BaseModel, Field


class AdminStatsOut(BaseModel):
    total_users: int
    active_alerts: int
    total_recommendations: int
    ai_spend_usd: float


class AIUsageEntryOut(BaseModel):
    provider: str
    model: str
    agent: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: datetime | None


class RunAgentAccepted(BaseModel):
    task_id: str
    agent: str


class AdminSettingsOut(BaseModel):
    ai_provider: str
    ai_fallback_providers: list[str]
    score_weights: dict[str, float]


class UpdateAdminSettingsRequest(BaseModel):
    score_weights: dict[str, float] | None = Field(default=None)

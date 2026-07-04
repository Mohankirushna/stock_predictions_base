"""Pydantic schema for the AI's qualitative recommendation. The master
score and risk/reward ratio are computed deterministically by the scoring
engine and in the agent itself — never trusted from model arithmetic."""
from pydantic import BaseModel, Field

from app.application.agents.schema_types import StrList

SYSTEM_PROMPT = (
    "You are an investment research analyst. Using ONLY the provided data "
    "context (technicals, fundamentals, news, market conditions, and the "
    "computed master score), propose research guidance: an action, a "
    "plausible entry price zone, a stop loss, three ascending take-profit "
    "levels, a holding period, concrete pros and cons grounded in the data, "
    "a clear explanation, and — critically — an uncertainty note stating "
    "what could invalidate this view. Never claim certainty. This is "
    "research guidance, not a trade order."
)


class RecommendationOutput(BaseModel):
    action: str = Field(pattern="^(strong_buy|buy|hold|reduce|avoid)$")
    entry_zone_low: float = Field(gt=0)
    entry_zone_high: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit_1: float = Field(gt=0)
    take_profit_2: float = Field(gt=0)
    take_profit_3: float = Field(gt=0)
    holding_period: str = Field(pattern="^(swing|short|medium|long)$")
    confidence: float = Field(ge=0.0, le=0.97)
    pros: StrList = Field(default_factory=list)
    cons: StrList = Field(default_factory=list)
    explanation: str = Field(min_length=1)
    uncertainty_note: str = Field(min_length=1)

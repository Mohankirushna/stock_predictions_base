"""Pydantic schema for the AI's ranked opportunity picks. `confidence` is
capped at 0.98 in the schema itself — a second, independent guard on top of
the domain's own <0.99 invariant — so a model that tries to claim certainty
fails validation before it ever reaches domain construction."""
from pydantic import BaseModel, Field

from app.application.agents.schema_types import StrList

SYSTEM_PROMPT = (
    "You are an equity screener. From the candidate companies below (with "
    "sector, valuation, and technical-trend context), select up to {max_picks} "
    "genuine opportunities NOT already on any watchlist. For each: give "
    "concrete reasons grounded in the provided data, a confidence level "
    "(never above 0.98 — markets are uncertain), concrete catalysts, the "
    "key risk, and a plausible entry price zone. Only pick symbols from the "
    "candidate list — never invent a symbol. If nothing stands out, return "
    "an empty list rather than forcing weak picks."
)


class OpportunityItemOutput(BaseModel):
    symbol: str
    reasons: StrList = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=0.98)
    catalysts: StrList = Field(default_factory=list)
    risk: str = Field(min_length=1)
    entry_zone_low: float = Field(gt=0)
    entry_zone_high: float = Field(gt=0)


class OpportunityScanOutput(BaseModel):
    opportunities: list[OpportunityItemOutput] = Field(default_factory=list, max_length=20)

"""Pydantic schema for the AI's structured news-analysis output.

Lives in the application layer, not the domain — the domain stays
framework-free (stdlib only, per app/domain's architecture rule). Field
constraints mirror NewsAnalysis's own invariants, so malformed model output
fails validation (and gets retried by the provider's chat_structured())
before it ever reaches the domain layer.
"""
from pydantic import BaseModel, Field

from app.application.agents.schema_types import StrList
from app.domain.intelligence.news import NewsAnalysis


class NewsAnalysisOutput(BaseModel):
    sentiment: float = Field(ge=-1.0, le=1.0, description="-1 (very negative) to 1 (very positive)")
    importance: int = Field(ge=0, le=10, description="How market-moving this news is, 0-10")
    summary: str = Field(min_length=1, description="A concise, factual summary of the article")
    risks: StrList = Field(default_factory=list, description="Risks this news implies")
    opportunities: StrList = Field(default_factory=list, description="Opportunities this news implies")
    industry: str = Field(default="", description="The primary industry this news affects")
    expected_impact: str = Field(default="", description="Expected short-term impact on the stock/sector")
    mentioned_symbols: list[str] = Field(default_factory=list, description="Ticker symbols explicitly mentioned")


def to_domain(output: NewsAnalysisOutput) -> NewsAnalysis:
    return NewsAnalysis(
        sentiment=output.sentiment, importance=output.importance, summary=output.summary,
        risks=tuple(output.risks), opportunities=tuple(output.opportunities),
        industry=output.industry, expected_impact=output.expected_impact,
        mentioned_symbols=tuple(output.mentioned_symbols),
    )

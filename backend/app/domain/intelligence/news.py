from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.common.entity import AggregateRoot
from app.domain.common.errors import InvariantViolation


@dataclass(frozen=True)
class NewsAnalysis:
    """Structured output of the News Intelligence Agent for one article."""

    sentiment: float  # -1.0 (very negative) .. 1.0 (very positive)
    importance: int  # 0–10
    summary: str
    risks: tuple[str, ...] = ()
    opportunities: tuple[str, ...] = ()
    industry: str = ""
    expected_impact: str = ""
    mentioned_symbols: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not -1.0 <= self.sentiment <= 1.0:
            raise InvariantViolation(f"sentiment out of range: {self.sentiment}")
        if not 0 <= self.importance <= 10:
            raise InvariantViolation(f"importance out of range: {self.importance}")
        if not self.summary.strip():
            raise InvariantViolation("analysis summary must not be empty")


@dataclass(kw_only=True, eq=False)
class NewsArticle(AggregateRoot):
    source: str
    url: str
    title: str
    content: str = ""
    published_at: datetime | None = None
    company_id: UUID | None = None
    collected_at: datetime | None = None
    analysis: NewsAnalysis | None = None  # None until the agent runs
    analyzed_at: datetime | None = None
    embedding_id: str | None = None
    extra_symbols: list[str] = field(default_factory=list)

    @property
    def is_analyzed(self) -> bool:
        return self.analysis is not None

    def attach_analysis(self, analysis: NewsAnalysis, at: datetime) -> None:
        self.analysis = analysis
        self.analyzed_at = at
        self.touch()

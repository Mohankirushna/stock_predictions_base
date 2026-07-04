from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from app.domain.common.entity import AggregateRoot


class ReportSection(StrEnum):
    COMPETITION = "competition"
    PRODUCTS = "products"
    MANAGEMENT = "management"
    MOAT = "moat"
    INDUSTRY = "industry"
    POLICIES = "policies"
    GROWTH = "growth"
    REGULATORY_RISKS = "regulatory_risks"
    ACQUISITIONS = "acquisitions"
    CATALYSTS = "catalysts"


@dataclass(frozen=True)
class SectionContent:
    text: str
    sources: tuple[str, ...] = ()  # urls / news ids backing the claims


@dataclass(kw_only=True, eq=False)
class ResearchReport(AggregateRoot):
    company_id: UUID
    generated_by: str  # agent name
    ai_provider: str = ""
    ai_model: str = ""
    summary: str = ""
    sections: dict[ReportSection, SectionContent] = field(default_factory=dict)
    embedding_id: str | None = None
    version: int = 1

    def missing_sections(self) -> list[ReportSection]:
        return [s for s in ReportSection if s not in self.sections]

    @property
    def is_complete(self) -> bool:
        return not self.missing_sections()

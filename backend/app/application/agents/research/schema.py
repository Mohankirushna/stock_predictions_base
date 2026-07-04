"""Pydantic schema for the Research Agent's 10-section report output.

Field names deliberately match ReportSection enum values one-to-one, so
mapping to the domain is mechanical and a missing section is a validation
error, not a silent gap.
"""
from pydantic import BaseModel, Field

from app.domain.research.report import ReportSection, SectionContent


class SectionOut(BaseModel):
    text: str = Field(min_length=1, description="The section's analysis, grounded in the provided data")
    sources: list[str] = Field(
        default_factory=list,
        description="URLs or data references from the provided context that back this section",
    )


class ResearchReportOutput(BaseModel):
    summary: str = Field(min_length=1, description="Executive summary of the whole report")
    competition: SectionOut
    products: SectionOut
    management: SectionOut
    moat: SectionOut
    industry: SectionOut
    policies: SectionOut
    growth: SectionOut
    regulatory_risks: SectionOut
    acquisitions: SectionOut
    catalysts: SectionOut


def to_domain_sections(output: ResearchReportOutput) -> dict[ReportSection, SectionContent]:
    return {
        section: SectionContent(
            text=getattr(output, section.value).text,
            sources=tuple(getattr(output, section.value).sources),
        )
        for section in ReportSection
    }

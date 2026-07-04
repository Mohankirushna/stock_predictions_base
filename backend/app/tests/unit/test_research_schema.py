import pytest
from pydantic import ValidationError

from app.application.agents.research.schema import (
    ResearchReportOutput,
    SectionOut,
    to_domain_sections,
)
from app.domain.research.report import ReportSection


def _full_output(**overrides) -> ResearchReportOutput:
    sections = {
        s.value: SectionOut(text=f"{s.value} analysis", sources=[f"https://example.com/{s.value}"])
        for s in ReportSection
    }
    sections.update(overrides)
    return ResearchReportOutput(summary="Executive summary.", **sections)


def test_all_ten_sections_map_to_domain() -> None:
    domain_sections = to_domain_sections(_full_output())
    assert set(domain_sections) == set(ReportSection)
    assert domain_sections[ReportSection.MOAT].text == "moat analysis"
    assert domain_sections[ReportSection.MOAT].sources == ("https://example.com/moat",)


def test_missing_section_is_a_validation_error() -> None:
    sections = {
        s.value: SectionOut(text="x") for s in ReportSection if s is not ReportSection.CATALYSTS
    }
    with pytest.raises(ValidationError):
        ResearchReportOutput(summary="s", **sections)


def test_empty_section_text_rejected() -> None:
    with pytest.raises(ValidationError):
        _full_output(moat=SectionOut(text=""))


def test_report_from_full_output_is_complete() -> None:
    from uuid import uuid4

    from app.domain.research.report import ResearchReport

    report = ResearchReport(
        company_id=uuid4(), generated_by="research",
        sections=to_domain_sections(_full_output()),
    )
    assert report.is_complete
    assert report.missing_sections() == []

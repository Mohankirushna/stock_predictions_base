import pytest
from pydantic import ValidationError

from app.application.agents.news_intelligence.schema import NewsAnalysisOutput, to_domain
from app.domain.intelligence.news import NewsAnalysis


def test_valid_output_constructs() -> None:
    output = NewsAnalysisOutput(
        sentiment=0.6, importance=7, summary="Strong earnings beat.",
        risks=["margin compression"], opportunities=["new product line"],
        industry="Technology", expected_impact="Likely short-term rally",
        mentioned_symbols=["AAPL"],
    )
    assert output.sentiment == 0.6


def test_sentiment_out_of_bounds_rejected() -> None:
    with pytest.raises(ValidationError):
        NewsAnalysisOutput(sentiment=1.5, importance=5, summary="x")


def test_importance_out_of_bounds_rejected() -> None:
    with pytest.raises(ValidationError):
        NewsAnalysisOutput(sentiment=0.0, importance=11, summary="x")


def test_empty_summary_rejected() -> None:
    with pytest.raises(ValidationError):
        NewsAnalysisOutput(sentiment=0.0, importance=5, summary="")


def test_defaults_are_empty_collections() -> None:
    output = NewsAnalysisOutput(sentiment=0.0, importance=5, summary="Neutral update.")
    assert output.risks == []
    assert output.opportunities == []
    assert output.mentioned_symbols == []


def test_to_domain_maps_all_fields() -> None:
    output = NewsAnalysisOutput(
        sentiment=-0.3, importance=8, summary="Regulatory probe announced.",
        risks=["fines"], opportunities=[], industry="Finance",
        expected_impact="Negative", mentioned_symbols=["JPM", "BAC"],
    )
    analysis = to_domain(output)
    assert isinstance(analysis, NewsAnalysis)
    assert analysis.sentiment == -0.3
    assert analysis.importance == 8
    assert analysis.risks == ("fines",)
    assert analysis.mentioned_symbols == ("JPM", "BAC")

"""Prompt construction for the News Intelligence Agent."""
from app.domain.intelligence.news import NewsArticle

SYSTEM_PROMPT = (
    "You are a financial news analyst. Read the article and extract a "
    "structured analysis: sentiment, importance, a concise summary, risks, "
    "opportunities, the primary industry affected, the expected short-term "
    "impact, and any stock ticker symbols explicitly mentioned. Be factual "
    "and conservative — do not speculate beyond what the article states."
)


def build_user_prompt(article: NewsArticle) -> str:
    body = article.content or article.title
    return f"Title: {article.title}\nSource: {article.source}\n\n{body}"

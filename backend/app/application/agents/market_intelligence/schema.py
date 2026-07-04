"""Pydantic schema for the AI half of Agent 5: the macro narrative."""
from pydantic import BaseModel, Field

from app.application.agents.schema_types import StrList

SYSTEM_PROMPT = (
    "You are a macro market strategist. Given today's market indicators, "
    "write a brief, factual macro narrative for investors. Note key risks "
    "and a one-line outlook. Never claim certainty; markets are uncertain."
)


class MacroNarrativeOutput(BaseModel):
    narrative: str = Field(min_length=1, description="2-4 sentence macro summary of current conditions")
    risks: StrList = Field(default_factory=list, description="Key macro risks right now")
    outlook: str = Field(default="", description="One-line forward outlook, hedged appropriately")

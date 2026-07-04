from decimal import Decimal

from pydantic import BaseModel


class OpportunityOut(BaseModel):
    symbol: str
    company_name: str
    reasons: list[str]
    confidence: float
    catalysts: list[str]
    risk: str
    entry_zone_low: Decimal
    entry_zone_high: Decimal


class GenerateReportAccepted(BaseModel):
    task_id: str
    symbol: str


class TaskStatusOut(BaseModel):
    task_id: str
    status: str
    result: dict | None = None

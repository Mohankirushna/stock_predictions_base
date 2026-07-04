from pydantic import BaseModel


class LeaderboardEntryOut(BaseModel):
    sector: str
    horizon: str
    rolling_accuracy: float
    sample_size: int

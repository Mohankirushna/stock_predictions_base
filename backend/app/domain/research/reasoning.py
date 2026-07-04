from dataclasses import dataclass, field
from typing import Any

from app.domain.common.entity import Entity


@dataclass(kw_only=True, eq=False)
class AIReasoning(Entity):
    """Full audit trail of one AI agent invocation — what it saw, what it said,
    and what it cost. Every AI-generated artifact links back to one of these."""

    agent: str
    ai_provider: str
    ai_model: str
    prompt_hash: str = ""
    inputs_digest: dict[str, Any] = field(default_factory=dict)
    raw_output: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0

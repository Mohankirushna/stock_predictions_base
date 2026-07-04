"""AIProvider port — THE abstraction every AI agent depends on.

Agents call `AIProvider.chat()` / `chat_structured()` and never import a
concrete provider (Gemini, Claude, OpenAI, Groq, OpenRouter, Ollama,
DeepSeek, Mistral). Adapters live in app/infrastructure/ai/providers and are
selected by configuration; swapping providers requires zero agent changes.
"""
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, TypeVar, runtime_checkable


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True)
class ChatRequest:
    messages: tuple[ChatMessage, ...]
    temperature: float = 0.2
    max_tokens: int = 4096
    agent: str = ""  # calling agent name — used for routing, overrides, cost attribution
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def of(cls, system: str, user: str, *, agent: str = "", **kwargs: Any) -> "ChatRequest":
        return cls(
            messages=(
                ChatMessage(ChatRole.SYSTEM, system),
                ChatMessage(ChatRole.USER, user),
            ),
            agent=agent,
            **kwargs,
        )


@dataclass(frozen=True)
class ChatUsage:
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


@dataclass(frozen=True)
class ChatResponse:
    content: str
    provider: str
    model: str
    usage: ChatUsage = field(default_factory=ChatUsage)
    raw: dict[str, Any] = field(default_factory=dict)


TStructured = TypeVar("TStructured")


@runtime_checkable
class AIProvider(Protocol):
    """Implemented by every provider adapter and by the fallback router."""

    name: str

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Free-form completion."""
        ...

    async def chat_structured(
        self, request: ChatRequest, schema: type[TStructured]
    ) -> tuple[TStructured, ChatResponse]:
        """Completion validated against `schema` (a pydantic model class).

        The adapter handles provider-specific JSON modes and retries invalid
        output; agents always receive a validated instance plus the raw
        response for the AIReasoning audit trail.
        """
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embedding vectors for semantic search (Qdrant)."""
        ...

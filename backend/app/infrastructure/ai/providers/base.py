"""Shared provider base.

Every concrete adapter implements only `chat()` (and `embed()` where the
vendor supports it). `chat_structured()` has one default implementation
here — schema-guided prompting + validation + a single self-correction
retry — so agents get identical structured-output behavior regardless of
which of the 8 providers is configured.
"""
import json
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.core.errors import AIProviderError
from app.domain.ports.ai_provider import ChatMessage, ChatRequest, ChatResponse, ChatRole

TStructured = TypeVar("TStructured", bound=BaseModel)

_STRUCTURED_INSTRUCTION = (
    "Respond with ONLY a single valid JSON object matching this JSON Schema. "
    "No prose, no markdown code fences, no commentary — the entire response "
    "must be parseable JSON.\n\nSchema:\n{schema}"
)
_MAX_STRUCTURED_ATTEMPTS = 2


class BaseAIProvider(ABC):
    name: str

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise AIProviderError(f"{self.name} does not support embeddings")

    async def chat_structured(
        self, request: ChatRequest, schema: type[TStructured]
    ) -> tuple[TStructured, ChatResponse]:
        schema_json = json.dumps(schema.model_json_schema())
        attempt_request = self._with_schema_instruction(request, schema_json)
        last_error: Exception | None = None
        last_response: ChatResponse | None = None

        for attempt in range(_MAX_STRUCTURED_ATTEMPTS):
            response = await self.chat(attempt_request)
            last_response = response
            try:
                data = self._extract_json(response.content)
                if isinstance(data, list) and len(schema.model_fields) == 1:
                    # Small models frequently drop the wrapper object for a
                    # single-field, list-valued schema and return the bare
                    # array — structurally equivalent, so reshape rather
                    # than burn a retry (or the whole fallback chain) on it.
                    data = {next(iter(schema.model_fields)): data}
                return schema.model_validate(data), response
            except Exception as exc:  # noqa: BLE001 — json/validation errors both retried
                last_error = exc
                if attempt + 1 < _MAX_STRUCTURED_ATTEMPTS:
                    attempt_request = self._with_correction(attempt_request, exc)

        raise AIProviderError(
            f"{self.name} failed to produce valid structured output after "
            f"{_MAX_STRUCTURED_ATTEMPTS} attempts: {last_error}",
            {"last_content": last_response.content if last_response else ""},
        )

    @staticmethod
    def _with_schema_instruction(request: ChatRequest, schema_json: str) -> ChatRequest:
        instruction = ChatMessage(ChatRole.SYSTEM, _STRUCTURED_INSTRUCTION.format(schema=schema_json))
        return ChatRequest(
            messages=(*request.messages, instruction),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            agent=request.agent,
            metadata=request.metadata,
        )

    @staticmethod
    def _with_correction(request: ChatRequest, error: Exception) -> ChatRequest:
        correction = ChatMessage(
            ChatRole.USER,
            f"Your previous response was not valid JSON matching the schema ({error}). "
            "Return ONLY the corrected JSON object.",
        )
        return ChatRequest(
            messages=(*request.messages, correction),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            agent=request.agent,
            metadata=request.metadata,
        )

    @staticmethod
    def _extract_json(content: str) -> dict:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        return json.loads(text.strip())

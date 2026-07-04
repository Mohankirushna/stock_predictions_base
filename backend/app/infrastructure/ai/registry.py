"""Maps a provider name (from config) to a constructed adapter instance.

This is the ONLY place that imports concrete provider classes. Agents and
the router never do — they depend on the AIProvider port.
"""
from collections.abc import Callable

from app.core.config import AISettings
from app.core.errors import AIProviderError
from app.infrastructure.ai.providers.base import BaseAIProvider
from app.infrastructure.ai.providers.claude import ClaudeProvider
from app.infrastructure.ai.providers.deepseek import DeepSeekProvider
from app.infrastructure.ai.providers.gemini import GeminiProvider
from app.infrastructure.ai.providers.groq import GroqProvider
from app.infrastructure.ai.providers.mistral import MistralProvider
from app.infrastructure.ai.providers.ollama import OllamaProvider
from app.infrastructure.ai.providers.openai import OpenAIProvider
from app.infrastructure.ai.providers.openrouter import OpenRouterProvider

_FACTORIES: dict[str, Callable[[AISettings], BaseAIProvider]] = {
    "gemini": lambda s: GeminiProvider(s.gemini_api_key),
    "claude": lambda s: ClaudeProvider(s.anthropic_api_key),
    "openai": lambda s: OpenAIProvider(s.openai_api_key),
    "groq": lambda s: GroqProvider(s.groq_api_key),
    "openrouter": lambda s: OpenRouterProvider(s.openrouter_api_key),
    "ollama": lambda s: OllamaProvider(s.ollama_base_url, model=s.ollama_model or None),
    "deepseek": lambda s: DeepSeekProvider(s.deepseek_api_key),
    "mistral": lambda s: MistralProvider(s.mistral_api_key),
}


def build_provider(name: str, settings: AISettings) -> BaseAIProvider:
    try:
        factory = _FACTORIES[name]
    except KeyError:
        raise AIProviderError(f"unknown AI provider: {name!r}") from None
    return factory(settings)


def available_providers() -> list[str]:
    return sorted(_FACTORIES)

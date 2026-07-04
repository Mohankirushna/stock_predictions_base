import pytest

from app.core.config import AISettings
from app.core.errors import AIProviderError
from app.infrastructure.ai.registry import available_providers, build_provider


def test_available_providers_lists_all_eight() -> None:
    assert available_providers() == [
        "claude", "deepseek", "gemini", "groq", "mistral", "ollama", "openai", "openrouter",
    ]


def test_unknown_provider_raises() -> None:
    with pytest.raises(AIProviderError, match="unknown AI provider"):
        build_provider("not-a-real-provider", AISettings())


@pytest.mark.parametrize("name", ["claude", "gemini", "openai", "groq", "openrouter", "deepseek", "mistral"])
def test_key_requiring_providers_reject_missing_key(name: str) -> None:
    with pytest.raises(AIProviderError, match="missing API key"):
        build_provider(name, AISettings())


def test_ollama_does_not_require_a_key() -> None:
    provider = build_provider("ollama", AISettings(ollama_base_url="http://localhost:11434"))
    assert provider.name == "ollama"
    assert provider.base_url == "http://localhost:11434/v1"


def test_provider_constructs_once_key_is_present() -> None:
    provider = build_provider("openai", AISettings(openai_api_key="sk-test"))
    assert provider.name == "openai"

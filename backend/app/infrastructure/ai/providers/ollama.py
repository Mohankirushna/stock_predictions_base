import httpx

from app.infrastructure.ai.providers.openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """Local inference via Ollama's OpenAI-compatible endpoint — no API key,
    no per-token cost."""

    name = "ollama"
    default_model = "llama3.1"
    embedding_model = "nomic-embed-text"
    requires_api_key = False
    pricing_per_million = (0.0, 0.0)

    def __init__(
        self,
        base_url: str,
        model: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = f"{base_url.rstrip('/')}/v1"
        super().__init__(api_key="", model=model, transport=transport)

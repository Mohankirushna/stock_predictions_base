from app.core.errors import AIProviderError
from app.infrastructure.ai.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    """Groq serves open-weight models at very low latency; no embeddings API."""

    name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    default_model = "llama-3.3-70b-versatile"
    pricing_per_million = (0.59, 0.79)  # illustrative

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise AIProviderError("groq does not offer an embeddings API")

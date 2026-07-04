from app.infrastructure.ai.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """Routes to whichever underlying model is requested; pricing varies per
    model so per-call cost isn't computed here (usage tokens still logged)."""

    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    default_model = "meta-llama/llama-3.3-70b-instruct"
    pricing_per_million = (0.0, 0.0)
    extra_headers = {"HTTP-Referer": "https://localhost", "X-Title": "AI Investment Research Platform"}

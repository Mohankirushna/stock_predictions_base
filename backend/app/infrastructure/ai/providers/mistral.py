from app.infrastructure.ai.providers.openai_compatible import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    name = "mistral"
    base_url = "https://api.mistral.ai/v1"
    default_model = "mistral-small-latest"
    embedding_model = "mistral-embed"
    pricing_per_million = (0.20, 0.60)  # illustrative

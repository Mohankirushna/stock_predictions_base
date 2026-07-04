from app.infrastructure.ai.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    base_url = "https://api.deepseek.com/v1"
    default_model = "deepseek-chat"
    pricing_per_million = (0.27, 1.10)  # illustrative

from app.infrastructure.ai.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o-mini"
    embedding_model = "text-embedding-3-small"
    pricing_per_million = (0.15, 0.60)  # gpt-4o-mini, illustrative — update as pricing changes

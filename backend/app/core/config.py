"""Application configuration.

Every setting is env-driven (see .env.example). Nested groups use the
`GROUP__FIELD` convention, e.g. DB__HOST, AI__PROVIDER.
"""
from enum import StrEnum
from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "stocks"
    password: str = "stocks"
    name: str = "stocks"
    pool_size: int = 10

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_url(self) -> str:
        """For Alembic migrations and Celery contexts."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379/0"


class QdrantSettings(BaseModel):
    url: str = "http://localhost:6333"
    api_key: str = ""


class AuthSettings(BaseModel):
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""


class AISettings(BaseModel):
    """AI provider selection — the code never hardcodes a provider.

    `provider` is the platform default; `agent_overrides` maps an agent name
    (e.g. "research") to a different provider; `fallback_providers` are tried
    in order when the primary fails.
    """

    provider: str = "ollama"
    fallback_providers: list[str] = Field(default_factory=list)
    agent_overrides: dict[str, str] = Field(default_factory=dict)

    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    deepseek_api_key: str = ""
    mistral_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""  # empty = use the adapter's default ("llama3.1")

    def provider_for(self, agent: str) -> str:
        return self.agent_overrides.get(agent, self.provider)


class MarketDataSettings(BaseModel):
    # Primary quotes/history/company-info/fundamentals vendor — never
    # hardcoded, same "provider" convention as AI__PROVIDER. finnhub|yahoo_finance
    provider: str = "finnhub"
    alpha_vantage_api_key: str = ""
    finnhub_api_key: str = ""
    marketaux_api_key: str = ""
    # marketaux free tier is 100 requests/day — don't re-fetch news for the
    # same symbol more often than this.
    marketaux_min_interval_hours: int = 4
    # When set, scheduled agents operate on exactly this universe instead of
    # every row in `companies` — protects the real data pipeline (and a
    # tight free-tier vendor quota) from ever being derailed by stray rows
    # (e.g. test fixtures sharing a dev database with the running app).
    tracked_symbols: list[str] = Field(default_factory=list)


class RateLimitSettings(BaseModel):
    enabled: bool = True
    default_per_minute: int = 120
    auth_per_minute: int = 10


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="",
        extra="ignore",
    )

    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = False
    app_secret_key: str = "insecure-dev-key-change-me"
    app_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    api_v1_prefix: str = "/api/v1"
    project_name: str = "AI Investment Research Platform"
    version: str = "0.1.0"

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    ai: AISettings = Field(default_factory=AISettings)
    market: MarketDataSettings = Field(default_factory=MarketDataSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)

    @property
    def is_production(self) -> bool:
        return self.app_env is Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()

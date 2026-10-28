"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Voice AI Interview Platform"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/voiceai"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_realtime_model: str = "gpt-realtime"
    openai_realtime_voice: str = "marin"
    interview_max_minutes: int = 12
    interview_max_questions: int = 6
    voice_client_secret_ttl_seconds: int = 600
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

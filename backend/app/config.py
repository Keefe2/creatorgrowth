"""Application configuration. All secrets come from the environment."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CreatorGrowth"
    env: str = "dev"
    database_url: str = "sqlite:///./creator_growth.db"

    jwt_secret: str = "change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    encryption_key: str = "change-me-to-a-fernet-key"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    login_rate_limit: str = "5/minute"
    register_rate_limit: str = "10/hour"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()

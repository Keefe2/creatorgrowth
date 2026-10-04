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

    # Serverless-safe DB rate limits (slowapi's in-memory counters do not
    # survive across serverless instances). Applied on top of slowapi.
    rl_login_ip_per_minute: int = 5
    rl_login_email_per_hour: int = 20
    rl_register_ip_per_hour: int = 10
    rl_otp_verify_ip_per_minute: int = 15
    rl_otp_resend_ip_per_hour: int = 10
    rl_refresh_ip_per_minute: int = 60

    # Email OTP verification
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()

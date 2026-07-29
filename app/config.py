"""Application configuration via environment variables."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SmartCart"
    app_env: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8904
    secret_key: str = Field(..., min_length=16)
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Database — SQLite for development, PostgreSQL for production
    # Examples:
    #   sqlite:///./smartcart.db
    #   postgresql+psycopg2://smartcart:smartcart@localhost:5432/smartcart
    database_url: str = "sqlite:///./smartcart.db"

    # CORS
    cors_origins: List[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8904",
    ]

    # Stripe
    stripe_secret_key: str = "sk_test_placeholder"
    stripe_publishable_key: str = "pk_test_placeholder"
    stripe_webhook_secret: str = "whsec_placeholder"
    currency: str = "usd"

    # OpenAI (optional)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Business
    default_tax_rate: float = 0.08
    default_shipping_flat: float = 5.99
    free_shipping_threshold: float = 75.00

    # Rate limiting
    rate_limit: str = "100/minute"

    # Admin seed
    admin_email: str = "admin@smartcart.com"
    admin_password: str = "Admin@12345"
    admin_full_name: str = "SmartCart Admin"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for dependency injection."""
    return Settings()

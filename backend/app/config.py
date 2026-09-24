from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings managed by pydantic-settings."""

    # Supabase credentials
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Paystack credentials
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""

    # Frontend CORS origin
    FRONTEND_URL: str = "http://localhost:5173"

    # Base URL for customer payment checkout pages
    PAYMENT_PAGE_BASE_URL: str = "https://incpay.vercel.app"

    # Minimum payment listed amount in GHS (₵)
    MIN_PAYMENT_AMOUNT: float = 1.0

    # Environment
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()

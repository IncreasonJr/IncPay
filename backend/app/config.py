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

    # Resend email credentials
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"

    # Frontend CORS origin
    FRONTEND_URL: str = "http://localhost:5173"

    # Base URL for customer payment checkout pages
    PAYMENT_PAGE_BASE_URL: str = "https://incpay.vercel.app"

    # Minimum payment listed amount in GHS (₵)
    MIN_PAYMENT_AMOUNT: float = 1.0

    # Maximum payment listed amount in GHS (₵) to prevent integer overflows or abuse
    MAX_PAYMENT_AMOUNT: float = 50000.0

    # Environment
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


def check_critical_settings(settings: Settings) -> list[str]:
    """Audit critical environment variables and return list of warnings."""
    warnings = []
    if not settings.SUPABASE_URL or "your-project" in settings.SUPABASE_URL:
        warnings.append("SUPABASE_URL is missing or using placeholder.")
    if not settings.SUPABASE_KEY or "your-anon-key" in settings.SUPABASE_KEY:
        warnings.append("SUPABASE_KEY is missing or using placeholder.")
    if not settings.PAYSTACK_SECRET_KEY or "sk_test_xxx" in settings.PAYSTACK_SECRET_KEY:
        warnings.append("PAYSTACK_SECRET_KEY is missing or using placeholder.")
    return warnings


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()


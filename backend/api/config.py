"""
API configuration using Pydantic Settings.

Loads configuration from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """API configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PRIZMS_",
        case_sensitive=False,
    )

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False

    # CORS settings
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Supabase settings (for auth)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Provider API keys (server-side)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_ai_api_key: str = ""
    xai_api_key: str = ""
    openrouter_api_key: str = ""

    # Stripe settings
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds


def get_settings() -> APISettings:
    """Get cached settings instance."""
    return APISettings()

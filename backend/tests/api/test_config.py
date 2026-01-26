"""Tests for API configuration."""

import pytest

from api.config import APISettings


class TestAPISettings:
    """Tests for APISettings class."""

    def test_default_values(self):
        """Should have sensible defaults."""
        settings = APISettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.debug is False
        assert settings.reload is False

    def test_env_override(self, monkeypatch):
        """Should load from environment variables."""
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("RELOAD", "true")
        settings = APISettings()
        assert settings.port == 9000
        assert settings.debug is True
        assert settings.reload is True

    def test_cors_defaults(self):
        """Should have CORS defaults."""
        settings = APISettings()
        assert "http://localhost:5173" in settings.cors_origins
        assert "http://localhost:3000" in settings.cors_origins
        assert settings.cors_allow_credentials is True
        assert settings.cors_allow_methods == ["*"]
        assert settings.cors_allow_headers == ["*"]

    def test_rate_limit_defaults(self):
        """Should have rate limit defaults."""
        settings = APISettings()
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window == 60

    def test_provider_api_keys_empty_by_default(self):
        """Provider API keys should be empty by default."""
        settings = APISettings()
        assert settings.anthropic_api_key == ""
        assert settings.openai_api_key == ""
        assert settings.google_api_key == ""
        assert settings.xai_api_key == ""
        assert settings.openrouter_api_key == ""

    def test_supabase_settings_empty_by_default(self):
        """Supabase settings should be empty by default."""
        settings = APISettings()
        assert settings.supabase_url == ""
        assert settings.supabase_anon_key == ""
        assert settings.supabase_service_role_key == ""
        assert settings.supabase_jwt_secret == ""

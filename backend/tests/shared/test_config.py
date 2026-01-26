"""Tests for shared/config.py."""

import pytest
from unittest.mock import patch
import os

from shared.config import Settings, get_settings


class TestSettings:
    def test_default_values(self):
        """Settings should have sensible defaults."""
        settings = Settings()
        assert settings.app_name == "Prizms API"
        assert settings.debug is False
        assert settings.port == 8000
        assert settings.host == "0.0.0.0"
        assert settings.app_version == "0.1.0"
        assert settings.frontend_url == "http://localhost:5173"
        assert settings.enable_usage_tracking is True
        assert settings.enable_billing is True

    def test_loads_from_env(self):
        """Settings should load from environment variables."""
        with patch.dict(os.environ, {"DEBUG": "true", "PORT": "9000"}):
            settings = Settings()
            assert settings.debug is True
            assert settings.port == 9000

    def test_loads_api_keys_from_env(self):
        """Settings should load API keys from environment variables."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "OPENAI_API_KEY": "test-openai-key",
        }):
            settings = Settings()
            assert settings.anthropic_api_key == "test-anthropic-key"
            assert settings.openai_api_key == "test-openai-key"

    def test_loads_supabase_config_from_env(self):
        """Settings should load Supabase configuration from environment variables."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        }):
            settings = Settings()
            assert settings.supabase_url == "https://test.supabase.co"
            assert settings.supabase_anon_key == "test-anon-key"
            assert settings.supabase_service_role_key == "test-service-key"


class TestGetSettings:
    def test_get_settings_returns_settings_instance(self):
        """get_settings should return a Settings instance."""
        # Clear the cache first
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_caches(self):
        """get_settings should return cached instance."""
        # Clear the cache first
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

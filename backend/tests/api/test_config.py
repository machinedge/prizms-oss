import pytest
from api.config import APISettings


class TestAPISettings:

    def test_default_values(self):
        """Should have sensible defaults."""
        settings = APISettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.debug is False

    def test_env_override(self, monkeypatch):
        """Should load from environment variables."""
        monkeypatch.setenv("PRIZMS_PORT", "9000")
        monkeypatch.setenv("PRIZMS_DEBUG", "true")
        settings = APISettings()
        assert settings.port == 9000
        assert settings.debug is True

"""Tests for debates module exceptions."""

import pytest

from modules.debates.exceptions import (
    DebateError,
    DebateNotFoundError,
    DebateAccessDeniedError,
    DebateAlreadyActiveError,
    DebateAlreadyCompletedError,
    DebateCancelledError,
    ProviderError,
)


class TestDebateError:
    def test_debate_error(self):
        """Should create a base debate error."""
        error = DebateError("Something went wrong", code="DEBATE_ERROR")
        assert str(error) == "Something went wrong"
        assert error.code == "DEBATE_ERROR"

    def test_debate_error_to_dict(self):
        """Should convert to dict for API responses."""
        error = DebateError("Test error", code="TEST", details={"key": "value"})
        result = error.to_dict()
        assert result["error"] == "TEST"
        assert result["message"] == "Test error"
        assert result["details"]["key"] == "value"


class TestDebateNotFoundError:
    def test_debate_not_found_error(self):
        """Should create not found error with debate ID."""
        error = DebateNotFoundError("debate-123")
        assert "Debate not found" in str(error)
        assert "debate-123" in str(error)
        assert error.code == "DEBATE_NOT_FOUND"
        assert error.details["debate_id"] == "debate-123"

    def test_debate_not_found_to_dict(self):
        """Should convert to dict."""
        error = DebateNotFoundError("debate-456")
        result = error.to_dict()
        assert result["error"] == "DEBATE_NOT_FOUND"
        assert result["details"]["debate_id"] == "debate-456"


class TestDebateAccessDeniedError:
    def test_debate_access_denied_error(self):
        """Should create access denied error with IDs."""
        error = DebateAccessDeniedError("debate-123", "user-456")
        assert "Access denied" in str(error)
        assert "debate-123" in str(error)
        assert error.code == "DEBATE_ACCESS_DENIED"
        assert error.details["debate_id"] == "debate-123"
        assert error.details["user_id"] == "user-456"

    def test_debate_access_denied_to_dict(self):
        """Should convert to dict."""
        error = DebateAccessDeniedError("debate-123", "user-456")
        result = error.to_dict()
        assert result["error"] == "DEBATE_ACCESS_DENIED"
        assert result["details"]["debate_id"] == "debate-123"
        assert result["details"]["user_id"] == "user-456"


class TestDebateAlreadyActiveError:
    def test_debate_already_active_error(self):
        """Should create already active error."""
        error = DebateAlreadyActiveError("debate-123")
        assert "already active" in str(error)
        assert error.code == "DEBATE_ALREADY_ACTIVE"
        assert error.details["debate_id"] == "debate-123"


class TestDebateAlreadyCompletedError:
    def test_debate_already_completed_error(self):
        """Should create already completed error."""
        error = DebateAlreadyCompletedError("debate-123")
        assert "already completed" in str(error)
        assert error.code == "DEBATE_ALREADY_COMPLETED"
        assert error.details["debate_id"] == "debate-123"


class TestDebateCancelledError:
    def test_debate_cancelled_error(self):
        """Should create cancelled error."""
        error = DebateCancelledError("debate-123")
        assert "cancelled" in str(error)
        assert error.code == "DEBATE_CANCELLED"
        assert error.details["debate_id"] == "debate-123"


class TestProviderError:
    def test_provider_error(self):
        """Should create provider error."""
        error = ProviderError("anthropic", "API rate limit exceeded")
        assert "Provider error" in str(error)
        assert "anthropic" in str(error)
        assert error.code == "PROVIDER_ERROR"
        assert error.details["provider"] == "anthropic"

    def test_provider_error_with_original_error(self):
        """Should include original error when provided."""
        error = ProviderError(
            "openai",
            "Request failed",
            original_error="Connection timeout",
        )
        assert error.details["original_error"] == "Connection timeout"

    def test_provider_error_to_dict(self):
        """Should convert to dict."""
        error = ProviderError("gemini", "Invalid API key")
        result = error.to_dict()
        assert result["error"] == "PROVIDER_ERROR"
        assert result["details"]["provider"] == "gemini"

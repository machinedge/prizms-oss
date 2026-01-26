"""Tests for usage module exceptions."""

import pytest

from modules.usage.exceptions import (
    UsageError,
    UnknownProviderError,
    UnknownModelError,
    InvalidTokenCountError,
    PricingFetchError,
)
from shared.exceptions import PrizmsError, ValidationError


class TestUsageError:
    def test_inherits_from_prizms_error(self):
        """UsageError should inherit from PrizmsError."""
        error = UsageError("Test error")
        assert isinstance(error, PrizmsError)

    def test_message(self):
        """Should store error message."""
        error = UsageError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"


class TestUnknownProviderError:
    def test_inherits_from_usage_error(self):
        """UnknownProviderError should inherit from UsageError."""
        error = UnknownProviderError("fake-provider")
        assert isinstance(error, UsageError)

    def test_error_message(self):
        """Should include provider in message."""
        error = UnknownProviderError("fake-provider")
        assert "fake-provider" in str(error)

    def test_error_code(self):
        """Should have correct error code."""
        error = UnknownProviderError("test")
        assert error.code == "UNKNOWN_PROVIDER"

    def test_error_details(self):
        """Should include provider in details."""
        error = UnknownProviderError("my-provider")
        assert error.details["provider"] == "my-provider"


class TestUnknownModelError:
    def test_inherits_from_usage_error(self):
        """UnknownModelError should inherit from UsageError."""
        error = UnknownModelError("anthropic", "fake-model")
        assert isinstance(error, UsageError)

    def test_error_message(self):
        """Should include provider and model in message."""
        error = UnknownModelError("anthropic", "fake-model")
        assert "anthropic" in str(error)
        assert "fake-model" in str(error)

    def test_error_code(self):
        """Should have correct error code."""
        error = UnknownModelError("test", "test")
        assert error.code == "UNKNOWN_MODEL"

    def test_error_details(self):
        """Should include provider and model in details."""
        error = UnknownModelError("anthropic", "claude-unknown")
        assert error.details["provider"] == "anthropic"
        assert error.details["model"] == "claude-unknown"


class TestInvalidTokenCountError:
    def test_inherits_from_validation_error(self):
        """InvalidTokenCountError should inherit from ValidationError."""
        error = InvalidTokenCountError("Negative tokens not allowed")
        assert isinstance(error, ValidationError)

    def test_error_message(self):
        """Should store error message."""
        error = InvalidTokenCountError("Token count must be positive")
        assert "Token count must be positive" in str(error)

    def test_error_code(self):
        """Should have correct error code."""
        error = InvalidTokenCountError("test")
        assert error.code == "INVALID_TOKEN_COUNT"


class TestPricingFetchError:
    def test_inherits_from_usage_error(self):
        """PricingFetchError should inherit from UsageError."""
        error = PricingFetchError("openrouter", "Connection failed")
        assert isinstance(error, UsageError)

    def test_error_message(self):
        """Should include provider and error in message."""
        error = PricingFetchError("openrouter", "API timeout")
        assert "openrouter" in str(error)
        assert "API timeout" in str(error)

    def test_error_code(self):
        """Should have correct error code."""
        error = PricingFetchError("test", "test")
        assert error.code == "PRICING_FETCH_ERROR"

    def test_error_details(self):
        """Should include provider and error in details."""
        error = PricingFetchError("openrouter", "Rate limited")
        assert error.details["provider"] == "openrouter"
        assert error.details["error"] == "Rate limited"


class TestExceptionSerialization:
    def test_usage_error_to_dict(self):
        """Should serialize to dict correctly."""
        error = UsageError("Test error", code="TEST_CODE", details={"key": "value"})
        result = error.to_dict()
        assert result["error"] == "TEST_CODE"
        assert result["message"] == "Test error"
        assert result["details"]["key"] == "value"

    def test_unknown_provider_to_dict(self):
        """Should serialize UnknownProviderError correctly."""
        error = UnknownProviderError("bad-provider")
        result = error.to_dict()
        assert result["error"] == "UNKNOWN_PROVIDER"
        assert "bad-provider" in result["message"]
        assert result["details"]["provider"] == "bad-provider"

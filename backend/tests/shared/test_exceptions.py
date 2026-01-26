"""Tests for shared/exceptions.py."""

import pytest

from shared.exceptions import (
    PrizmsError,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
)


class TestPrizmsError:
    def test_prizms_error_message(self):
        """PrizmsError should store message."""
        error = PrizmsError("Test error")
        assert error.message == "Test error"
        assert str(error) == "Test error"

    def test_prizms_error_default_code(self):
        """PrizmsError should default code to class name."""
        error = PrizmsError("Test error")
        assert error.code == "PrizmsError"

    def test_prizms_error_custom_code(self):
        """PrizmsError should accept custom code."""
        error = PrizmsError("Test error", code="CUSTOM_ERROR")
        assert error.code == "CUSTOM_ERROR"

    def test_prizms_error_default_details(self):
        """PrizmsError should default details to empty dict."""
        error = PrizmsError("Test error")
        assert error.details == {}

    def test_prizms_error_custom_details(self):
        """PrizmsError should accept custom details."""
        error = PrizmsError("Test error", details={"key": "value"})
        assert error.details == {"key": "value"}

    def test_prizms_error_to_dict(self):
        """PrizmsError should convert to dict."""
        error = PrizmsError("Test error", code="TEST_ERROR", details={"key": "value"})
        result = error.to_dict()

        assert result["error"] == "TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["details"]["key"] == "value"

    def test_prizms_error_to_dict_minimal(self):
        """PrizmsError.to_dict should work with minimal args."""
        error = PrizmsError("Test error")
        result = error.to_dict()

        assert result["error"] == "PrizmsError"
        assert result["message"] == "Test error"
        assert result["details"] == {}


class TestNotFoundError:
    def test_not_found_error_inherits_prizms_error(self):
        """NotFoundError should inherit from PrizmsError."""
        error = NotFoundError("Resource not found")
        assert isinstance(error, PrizmsError)

    def test_not_found_error_default_code(self):
        """NotFoundError should default code to class name."""
        error = NotFoundError("Resource not found")
        assert error.code == "NotFoundError"


class TestValidationError:
    def test_validation_error_inherits_prizms_error(self):
        """ValidationError should inherit from PrizmsError."""
        error = ValidationError("Invalid input")
        assert isinstance(error, PrizmsError)

    def test_validation_error_with_details(self):
        """ValidationError should support field-level details."""
        error = ValidationError(
            "Validation failed",
            details={"fields": {"email": "Invalid format"}}
        )
        assert error.details["fields"]["email"] == "Invalid format"


class TestAuthenticationError:
    def test_authentication_error_inherits_prizms_error(self):
        """AuthenticationError should inherit from PrizmsError."""
        error = AuthenticationError("Invalid token")
        assert isinstance(error, PrizmsError)


class TestAuthorizationError:
    def test_authorization_error_inherits_prizms_error(self):
        """AuthorizationError should inherit from PrizmsError."""
        error = AuthorizationError("Insufficient permissions")
        assert isinstance(error, PrizmsError)


class TestExternalServiceError:
    def test_external_service_error_inherits_prizms_error(self):
        """ExternalServiceError should inherit from PrizmsError."""
        error = ExternalServiceError("Connection failed", service="stripe")
        assert isinstance(error, PrizmsError)

    def test_external_service_error_stores_service(self):
        """ExternalServiceError should store service name."""
        error = ExternalServiceError("Connection failed", service="stripe")
        assert error.service == "stripe"

    def test_external_service_error_includes_service_in_details(self):
        """ExternalServiceError should include service in details."""
        error = ExternalServiceError("Connection failed", service="stripe")
        result = error.to_dict()

        assert result["details"]["service"] == "stripe"

    def test_external_service_error_preserves_other_details(self):
        """ExternalServiceError should preserve other details."""
        error = ExternalServiceError(
            "Connection failed",
            service="stripe",
            details={"status_code": 500}
        )
        result = error.to_dict()

        assert result["details"]["service"] == "stripe"
        assert result["details"]["status_code"] == 500

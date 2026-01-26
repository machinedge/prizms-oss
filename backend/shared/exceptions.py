"""
Base exception classes for the Prizms backend.

Each module should define its own exceptions that inherit from these bases.
This enables consistent error handling across the application.
"""

from typing import Optional, Any


class PrizmsError(Exception):
    """
    Base exception for all Prizms errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class NotFoundError(PrizmsError):
    """Resource not found."""

    pass


class ValidationError(PrizmsError):
    """Input validation failed."""

    pass


class AuthenticationError(PrizmsError):
    """Authentication failed (invalid or missing credentials)."""

    pass


class AuthorizationError(PrizmsError):
    """Authorization failed (insufficient permissions)."""

    pass


class ExternalServiceError(PrizmsError):
    """Error communicating with an external service."""

    def __init__(
        self,
        message: str,
        service: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)
        self.service = service
        self.details["service"] = service

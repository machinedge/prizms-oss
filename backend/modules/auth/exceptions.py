"""
Authentication module exceptions.

These exceptions are raised by the auth module and can be caught
by API error handlers to return appropriate HTTP responses.
"""

from shared.exceptions import AuthenticationError, AuthorizationError


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid or malformed."""

    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(message, code="INVALID_TOKEN")


class ExpiredTokenError(AuthenticationError):
    """Raised when a JWT token has expired."""

    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(message, code="TOKEN_EXPIRED")


class MissingTokenError(AuthenticationError):
    """Raised when no authentication token is provided."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, code="MISSING_TOKEN")


class UserNotFoundError(AuthenticationError):
    """Raised when the authenticated user doesn't exist in the database."""

    def __init__(self, user_id: str):
        super().__init__(
            f"User not found: {user_id}",
            code="USER_NOT_FOUND",
            details={"user_id": user_id},
        )


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions."""

    def __init__(self, required_role: str, user_role: str):
        super().__init__(
            f"Insufficient permissions. Required: {required_role}, has: {user_role}",
            code="INSUFFICIENT_PERMISSIONS",
            details={"required_role": required_role, "user_role": user_role},
        )

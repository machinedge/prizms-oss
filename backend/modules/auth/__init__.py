"""
Authentication module.

Handles JWT validation, user profile management, and auth middleware.

Public API:
- IAuthService: Interface for auth operations
- AuthenticatedUser: Minimal user info from JWT
- UserProfile: Full user profile
- Auth exceptions: InvalidTokenError, ExpiredTokenError, etc.
"""

from .interfaces import IAuthService
from .models import AuthenticatedUser, UserProfile, JWTPayload
from .exceptions import (
    InvalidTokenError,
    ExpiredTokenError,
    MissingTokenError,
    UserNotFoundError,
    InsufficientPermissionsError,
)

__all__ = [
    # Interface
    "IAuthService",
    # Models
    "AuthenticatedUser",
    "UserProfile",
    "JWTPayload",
    # Exceptions
    "InvalidTokenError",
    "ExpiredTokenError",
    "MissingTokenError",
    "UserNotFoundError",
    "InsufficientPermissionsError",
]

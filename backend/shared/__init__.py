"""
Shared infrastructure for Prizms backend.

This package contains cross-cutting concerns that are used by multiple modules:
- config: Centralized settings management
- database: Supabase client factory
- exceptions: Base exception classes

Note: Business logic should NOT go here. This is for infrastructure only.
"""

from .config import Settings, get_settings
from .database import get_supabase_client, get_supabase_user_client, reset_client_cache
from .exceptions import (
    PrizmsError,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
)
from .models import AuthenticatedUser

__all__ = [
    "Settings",
    "get_settings",
    "get_supabase_client",
    "get_supabase_user_client",
    "reset_client_cache",
    "PrizmsError",
    "NotFoundError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ExternalServiceError",
    "AuthenticatedUser",
]

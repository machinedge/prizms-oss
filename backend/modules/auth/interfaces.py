"""
Authentication module interface.

Other modules should depend on IAuthService, not the concrete implementation.
This enables testing with mocks and future extraction to a microservice.
"""

from typing import Protocol, Optional, runtime_checkable

from .models import AuthenticatedUser, UserProfile


@runtime_checkable
class IAuthService(Protocol):
    """
    Interface for authentication operations.

    This protocol defines the contract that the auth module exposes
    to other modules. Implementations must provide all these methods.
    """

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """
        Validate a JWT token and return the authenticated user.

        Args:
            token: JWT access token from Supabase Auth

        Returns:
            AuthenticatedUser with user ID and basic info

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        ...

    async def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Get a user's profile by their ID.

        Args:
            user_id: Supabase user ID (UUID)

        Returns:
            UserProfile if found, None otherwise
        """
        ...

    async def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Get a user's profile by their email.

        Args:
            email: User's email address

        Returns:
            UserProfile if found, None otherwise
        """
        ...

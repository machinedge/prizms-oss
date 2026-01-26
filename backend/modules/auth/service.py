"""
Authentication service implementation.

This is a stub implementation that will be completed in Story 12.
It provides the basic structure and can be used for testing.
"""

from typing import Optional
import jwt

from shared.config import get_settings
from shared.database import get_supabase_client

from .interfaces import IAuthService
from .models import AuthenticatedUser, UserProfile, JWTPayload
from .exceptions import (
    InvalidTokenError,
    ExpiredTokenError,
    MissingTokenError,
)


class AuthService(IAuthService):
    """
    Implementation of the authentication service.

    Uses Supabase JWT tokens for authentication and the Supabase
    database for user profile storage.
    """

    def __init__(self):
        self._settings = get_settings()
        self._db = get_supabase_client()

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """
        Validate a JWT token and return the authenticated user.

        This implementation validates Supabase JWTs using the JWT secret.
        """
        if not token:
            raise MissingTokenError()

        try:
            # Decode and validate the JWT
            payload = jwt.decode(
                token,
                self._settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

            jwt_payload = JWTPayload(**payload)

            return AuthenticatedUser(
                id=jwt_payload.sub,
                email=jwt_payload.email or "",
                role=jwt_payload.role,
            )

        except jwt.ExpiredSignatureError:
            raise ExpiredTokenError()
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(str(e))

    async def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Get a user's profile by their ID.

        Queries the Supabase auth.users table (via service role).
        """
        # TODO: Implement in Story 12
        # This will query the users table and return a UserProfile
        raise NotImplementedError("Will be implemented in Story 12")

    async def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Get a user's profile by their email.
        """
        # TODO: Implement in Story 12
        raise NotImplementedError("Will be implemented in Story 12")


# Verify the implementation satisfies the interface
def _verify_interface():
    """Type check that AuthService implements IAuthService."""
    service: IAuthService = AuthService()
    return service


# Module-level instance getter
_service_instance: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the auth service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AuthService()
    return _service_instance

"""
Authentication service implementation.

Validates Supabase JWT tokens and provides user authentication.
"""

from datetime import datetime, timezone
from typing import Optional
import jwt

from shared.config import get_settings
from shared.database import get_supabase_client
from shared.models import AuthenticatedUser

from .interfaces import IAuthService
from .models import UserProfile, JWTPayload
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

            # Determine if email is verified
            email_verified = jwt_payload.email_confirmed_at is not None

            # Convert iat timestamp to datetime for last_sign_in
            last_sign_in = datetime.fromtimestamp(jwt_payload.iat, tz=timezone.utc)

            return AuthenticatedUser(
                id=jwt_payload.sub,
                email=jwt_payload.email or "",
                email_verified=email_verified,
                last_sign_in=last_sign_in,
                role=jwt_payload.role if jwt_payload.role != "authenticated" else "user",
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


def reset_auth_service() -> None:
    """Reset the auth service singleton (for testing)."""
    global _service_instance
    _service_instance = None

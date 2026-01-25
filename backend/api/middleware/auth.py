"""
JWT Authentication middleware.

Validates Supabase JWT tokens and extracts user information.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timezone

from ..config import get_settings
from ..models.user import AuthenticatedUser, TokenPayload

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    """Authentication error with consistent format."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a Supabase JWT token.

    Args:
        token: The JWT token string

    Returns:
        TokenPayload with decoded claims

    Raises:
        AuthError: If token is invalid or expired
    """
    settings = get_settings()

    if not settings.supabase_jwt_secret:
        raise AuthError("Server authentication not configured")

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except JWTError as e:
        raise AuthError(f"Invalid token: {str(e)}")


def get_user_from_payload(payload: TokenPayload) -> AuthenticatedUser:
    """
    Convert JWT payload to AuthenticatedUser model.

    Args:
        payload: Decoded JWT payload

    Returns:
        AuthenticatedUser instance
    """
    return AuthenticatedUser(
        id=payload.sub,
        email=payload.email,
        email_verified=payload.email_confirmed_at is not None,
        last_sign_in=datetime.fromtimestamp(payload.iat, tz=timezone.utc),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """
    Dependency that requires authentication.

    Use this for endpoints that require a logged-in user.

    Usage:
        @router.get("/protected")
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    if credentials is None:
        raise AuthError("Missing authorization header")

    payload = decode_token(credentials.credentials)
    return get_user_from_payload(payload)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[AuthenticatedUser]:
    """
    Dependency that optionally extracts user if authenticated.

    Use this for endpoints that work with or without authentication.

    Usage:
        @router.get("/public")
        async def public_route(user: Optional[AuthenticatedUser] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello, {user.email}"}
            return {"message": "Hello, anonymous"}
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
        return get_user_from_payload(payload)
    except AuthError:
        return None


# Type aliases for cleaner route definitions
RequireAuth = Depends(get_current_user)
OptionalAuth = Depends(get_optional_user)

"""
User models for authentication.

These models represent authenticated user data extracted from JWT tokens.
"""

from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime


class AuthenticatedUser(BaseModel):
    """
    Represents an authenticated user from a valid JWT.

    This model is populated from the JWT claims and made available
    to route handlers via dependency injection.
    """
    model_config = ConfigDict(extra="ignore")  # Ignore extra fields from JWT

    id: str  # Supabase user UUID
    email: EmailStr
    email_verified: bool = False

    # Timestamps
    created_at: Optional[datetime] = None
    last_sign_in: Optional[datetime] = None

    # Future extensibility (not implemented yet)
    role: str = "user"  # Default role, prepared for future RBAC
    tier: str = "free"  # Default tier, prepared for future billing tiers


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # User ID
    email: str
    email_confirmed_at: Optional[str] = None
    aud: str  # Audience
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp

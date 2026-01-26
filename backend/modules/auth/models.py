"""
Authentication module data models.

These models define the data structures used by the auth module
and exposed to other modules through the interface.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class JWTPayload(BaseModel):
    """
    Decoded JWT token payload from Supabase.

    This matches the structure of Supabase Auth JWTs.
    """

    sub: str = Field(..., description="Subject (user ID)")
    email: Optional[str] = Field(None, description="User's email")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    aud: str = Field(default="authenticated", description="Audience")
    role: str = Field(default="authenticated", description="User role")

    # Supabase-specific claims
    app_metadata: dict = Field(default_factory=dict)
    user_metadata: dict = Field(default_factory=dict)


class AuthenticatedUser(BaseModel):
    """
    Represents an authenticated user in the system.

    This is the minimal user info needed for most operations.
    It's extracted from the JWT and used throughout the request lifecycle.
    """

    id: str = Field(..., description="User ID (UUID from Supabase)")
    email: str = Field(..., description="User's email address")
    role: str = Field(default="user", description="User role")

    model_config = {"frozen": True}  # Make immutable for safety


class UserProfile(BaseModel):
    """
    Full user profile with additional metadata.

    This includes information beyond what's in the JWT,
    fetched from the database when needed.
    """

    id: str = Field(..., description="User ID (UUID)")
    email: EmailStr = Field(..., description="Email address")
    display_name: Optional[str] = Field(None, description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: datetime = Field(..., description="Last update time")

    # Subscription/tier info (will be populated by billing module)
    tier: str = Field(default="free", description="Subscription tier")


class TokenValidationRequest(BaseModel):
    """Request to validate a token (used in tests/internal APIs)."""

    token: str = Field(..., description="JWT token to validate")


class TokenValidationResponse(BaseModel):
    """Response from token validation."""

    valid: bool = Field(..., description="Whether the token is valid")
    user: Optional[AuthenticatedUser] = Field(None, description="User if valid")
    error: Optional[str] = Field(None, description="Error message if invalid")

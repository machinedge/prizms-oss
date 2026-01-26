"""
Shared data models used across modules.

These models are shared infrastructure, not business logic.
Module-specific models should stay in their respective module directories.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class AuthenticatedUser(BaseModel):
    """
    Represents an authenticated user in the system.

    This model is populated from JWT claims and made available
    to route handlers via dependency injection.

    This is the minimal user info needed for most operations.
    It's extracted from the JWT and used throughout the request lifecycle.
    """

    id: str = Field(..., description="User ID (UUID from Supabase)")
    email: EmailStr = Field(..., description="User's email address")
    email_verified: bool = Field(default=False, description="Whether email is verified")

    # Timestamps (optional for backward compatibility)
    created_at: Optional[datetime] = Field(None, description="Account creation time")
    last_sign_in: Optional[datetime] = Field(None, description="Last sign-in time")

    # Future extensibility (not implemented yet)
    role: str = Field(default="user", description="User role (prepared for future RBAC)")
    tier: str = Field(default="free", description="Subscription tier (prepared for billing)")

    model_config = {
        "frozen": True,  # Make immutable for safety
        "extra": "ignore",  # Ignore extra fields from JWT
    }

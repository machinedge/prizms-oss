"""
User-related endpoints.

Provides endpoints for user profile and account management.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from shared.models import AuthenticatedUser
from ..middleware.auth import get_current_user

router = APIRouter()


class UserProfileResponse(BaseModel):
    """User profile response model."""

    id: str
    email: EmailStr
    email_verified: bool
    tier: str
    role: str


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    user: AuthenticatedUser = Depends(get_current_user),
) -> UserProfileResponse:
    """
    Get the current user's profile.

    Requires authentication.
    """
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified,
        tier=user.tier,
        role=user.role,
    )

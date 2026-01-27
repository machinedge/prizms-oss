"""
Shared test fixtures and utilities.

This module provides common test infrastructure used across all test modules.
"""

import pytest
from datetime import datetime, timezone, timedelta
import jwt  # PyJWT

from modules.auth.service import reset_auth_service


# Test JWT secret (only for testing - matches test_auth.py)
TEST_JWT_SECRET = "test-secret-key-for-testing-only"


def create_test_token(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    expired: bool = False,
    email_verified: bool = True,
) -> str:
    """
    Create a test JWT token for authentication.
    
    Args:
        user_id: User ID to include in the token
        email: Email to include in the token
        expired: If True, creates an expired token
        email_verified: Whether the email should be marked as verified
    
    Returns:
        JWT token string
    """
    now = datetime.now(timezone.utc)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)

    payload = {
        "sub": user_id,
        "email": email,
        "email_confirmed_at": now.isoformat() if email_verified else None,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def reset_auth_singleton():
    """Reset the auth service singleton before and after each test."""
    reset_auth_service()
    yield
    reset_auth_service()


@pytest.fixture
def test_user_id() -> str:
    """Provide a consistent test user ID."""
    return "test-user-123"


@pytest.fixture
def test_user_email() -> str:
    """Provide a consistent test user email."""
    return "test@example.com"


@pytest.fixture
def auth_token(test_user_id: str, test_user_email: str) -> str:
    """Create a valid auth token for testing."""
    return create_test_token(user_id=test_user_id, email=test_user_email)


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Create authorization headers with a valid token."""
    return {"Authorization": f"Bearer {auth_token}"}

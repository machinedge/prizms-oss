"""
Tests for shared models.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from shared.models import AuthenticatedUser


class TestAuthenticatedUser:
    """Tests for the AuthenticatedUser model in shared."""

    def test_create_with_required_fields(self):
        """Should create user with only required fields."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
        )
        assert user.id == "user-123"
        assert user.email == "test@example.com"

    def test_default_values(self):
        """Should have correct default values."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
        )
        assert user.email_verified is False
        assert user.role == "user"
        assert user.tier == "free"
        assert user.created_at is None
        assert user.last_sign_in is None

    def test_all_fields(self):
        """Should accept all fields."""
        now = datetime.now(timezone.utc)
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
            email_verified=True,
            created_at=now,
            last_sign_in=now,
            role="admin",
            tier="pro",
        )
        assert user.email_verified is True
        assert user.role == "admin"
        assert user.tier == "pro"
        assert user.created_at == now

    def test_email_validation(self):
        """Should validate email format."""
        with pytest.raises(ValidationError):
            AuthenticatedUser(
                id="user-123",
                email="not-an-email",
            )

    def test_immutability(self):
        """Should be frozen/immutable."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
        )
        with pytest.raises(ValidationError):
            user.id = "new-id"

    def test_extra_fields_ignored(self):
        """Should ignore extra fields."""
        # This should not raise even with extra fields
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
            extra_field="ignored",  # type: ignore
        )
        # Extra field should not be accessible
        assert not hasattr(user, "extra_field")

    def test_model_dump(self):
        """Should serialize to dict correctly."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
            email_verified=True,
        )
        data = user.model_dump()
        assert data["id"] == "user-123"
        assert data["email"] == "test@example.com"
        assert data["email_verified"] is True
        assert data["role"] == "user"
        assert data["tier"] == "free"

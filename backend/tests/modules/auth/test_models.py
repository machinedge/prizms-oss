import pytest
from datetime import datetime

from modules.auth.models import AuthenticatedUser, UserProfile, JWTPayload


class TestAuthenticatedUser:
    def test_create_user(self):
        """Should create an authenticated user."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
            role="user",
        )
        assert user.id == "user-123"
        assert user.email == "test@example.com"
        assert user.role == "user"

    def test_user_is_immutable(self):
        """AuthenticatedUser should be immutable."""
        user = AuthenticatedUser(id="user-123", email="test@example.com")
        with pytest.raises(Exception):  # Pydantic ValidationError
            user.id = "different-id"

    def test_default_role(self):
        """AuthenticatedUser should have default role 'user'."""
        user = AuthenticatedUser(id="user-123", email="test@example.com")
        assert user.role == "user"


class TestJWTPayload:
    def test_parse_jwt_payload(self):
        """Should parse JWT payload from dict."""
        data = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": 1704067200,
            "iat": 1704063600,
            "aud": "authenticated",
            "role": "authenticated",
        }
        payload = JWTPayload(**data)
        assert payload.sub == "user-123"
        assert payload.email == "test@example.com"

    def test_jwt_defaults(self):
        """JWTPayload should have sensible defaults."""
        data = {
            "sub": "user-123",
            "exp": 1704067200,
            "iat": 1704063600,
        }
        payload = JWTPayload(**data)
        assert payload.aud == "authenticated"
        assert payload.role == "authenticated"
        assert payload.app_metadata == {}
        assert payload.user_metadata == {}

    def test_jwt_with_metadata(self):
        """JWTPayload should parse custom metadata."""
        data = {
            "sub": "user-123",
            "exp": 1704067200,
            "iat": 1704063600,
            "app_metadata": {"provider": "google"},
            "user_metadata": {"name": "Test User"},
        }
        payload = JWTPayload(**data)
        assert payload.app_metadata == {"provider": "google"}
        assert payload.user_metadata == {"name": "Test User"}


class TestUserProfile:
    def test_default_tier(self):
        """UserProfile should default to free tier."""
        profile = UserProfile(
            id="user-123",
            email="test@example.com",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert profile.tier == "free"

    def test_optional_fields(self):
        """UserProfile should allow None for optional fields."""
        profile = UserProfile(
            id="user-123",
            email="test@example.com",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert profile.display_name is None
        assert profile.avatar_url is None

    def test_full_profile(self):
        """UserProfile should store all fields."""
        now = datetime.now()
        profile = UserProfile(
            id="user-123",
            email="test@example.com",
            display_name="Test User",
            avatar_url="https://example.com/avatar.png",
            created_at=now,
            updated_at=now,
            tier="premium",
        )
        assert profile.id == "user-123"
        assert profile.email == "test@example.com"
        assert profile.display_name == "Test User"
        assert profile.avatar_url == "https://example.com/avatar.png"
        assert profile.tier == "premium"

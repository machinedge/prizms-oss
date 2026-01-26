"""
Tests for JWT authentication middleware and user routes.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import jwt  # PyJWT
from fastapi.testclient import TestClient

from api.app import app
from api.middleware.auth import get_current_user, get_optional_user, AuthError
from shared.models import AuthenticatedUser
from modules.auth.models import JWTPayload
from modules.auth.exceptions import InvalidTokenError, ExpiredTokenError, MissingTokenError
from modules.auth.service import reset_auth_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_auth_singleton():
    """Reset the auth service singleton before each test."""
    reset_auth_service()
    yield
    reset_auth_service()

# Test JWT secret (only for testing)
TEST_JWT_SECRET = "test-secret-key-for-testing-only"


def create_test_token(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    expired: bool = False,
    email_verified: bool = True,
) -> str:
    """Create a test JWT token."""
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


class TestAuthMiddleware:
    """Tests for auth middleware functions."""

    def test_missing_auth_header(self):
        """Request without auth header should return 401."""
        response = client.get("/api/users/me")
        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["detail"]

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_protected_route_with_valid_token(self, mock_db, mock_settings):
        """Protected route should work with valid token."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        token = create_test_token()
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-user-123"
        assert data["email"] == "test@example.com"
        assert data["email_verified"] is True
        assert data["role"] == "user"
        assert data["tier"] == "free"

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_expired_token_returns_401(self, mock_db, mock_settings):
        """Expired token should return 401."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        token = create_test_token(expired=True)
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_invalid_token_returns_401(self, mock_db, mock_settings):
        """Invalid token should return 401."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_wrong_secret_returns_401(self, mock_db, mock_settings):
        """Token signed with wrong secret should return 401."""
        mock_settings.return_value.supabase_jwt_secret = "different-secret"
        mock_db.return_value = MagicMock()

        token = create_test_token()  # Signed with TEST_JWT_SECRET
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_unverified_email(self, mock_db, mock_settings):
        """Token with unverified email should set email_verified to False."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        token = create_test_token(email_verified=False)
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email_verified"] is False


class TestAuthError:
    """Tests for AuthError exception."""

    def test_auth_error_status_code(self):
        """AuthError should have 401 status code."""
        error = AuthError("Test error")
        assert error.status_code == 401

    def test_auth_error_headers(self):
        """AuthError should include WWW-Authenticate header."""
        error = AuthError("Test error")
        assert error.headers == {"WWW-Authenticate": "Bearer"}

    def test_auth_error_detail(self):
        """AuthError should include the detail message."""
        error = AuthError("Custom message")
        assert error.detail == "Custom message"


class TestJWTPayload:
    """Tests for JWTPayload model."""

    def test_jwt_payload_required_fields(self):
        """JWTPayload should require sub and exp fields."""
        payload = JWTPayload(
            sub="user-123",
            exp=9999999999,
            iat=1704067200,
        )
        assert payload.sub == "user-123"
        assert payload.exp == 9999999999

    def test_jwt_payload_optional_fields(self):
        """JWTPayload should have optional fields with defaults."""
        payload = JWTPayload(
            sub="user-123",
            exp=9999999999,
            iat=1704067200,
        )
        assert payload.email is None
        assert payload.email_confirmed_at is None
        assert payload.aud == "authenticated"
        assert payload.role == "authenticated"

    def test_jwt_payload_all_fields(self):
        """JWTPayload should accept all fields."""
        payload = JWTPayload(
            sub="user-123",
            email="test@example.com",
            email_confirmed_at="2024-01-01T00:00:00Z",
            aud="authenticated",
            exp=9999999999,
            iat=1704067200,
            role="admin",
            app_metadata={"key": "value"},
            user_metadata={"name": "Test User"},
        )
        assert payload.email == "test@example.com"
        assert payload.email_confirmed_at == "2024-01-01T00:00:00Z"
        assert payload.role == "admin"
        assert payload.app_metadata == {"key": "value"}


class TestAuthenticatedUser:
    """Tests for AuthenticatedUser model."""

    def test_authenticated_user_required_fields(self):
        """AuthenticatedUser should require id and email."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
        )
        assert user.id == "user-123"
        assert user.email == "test@example.com"

    def test_authenticated_user_defaults(self):
        """AuthenticatedUser should have sensible defaults."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
        )
        assert user.email_verified is False
        assert user.role == "user"
        assert user.tier == "free"
        assert user.created_at is None
        assert user.last_sign_in is None

    def test_authenticated_user_all_fields(self):
        """AuthenticatedUser should accept all fields."""
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
        assert user.last_sign_in == now

    def test_authenticated_user_is_frozen(self):
        """AuthenticatedUser should be immutable."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
        )
        with pytest.raises(Exception):  # ValidationError for frozen models
            user.id = "new-id"

    def test_authenticated_user_ignores_extra_fields(self):
        """AuthenticatedUser should ignore extra fields."""
        user = AuthenticatedUser(
            id="user-123",
            email="test@example.com",
            unknown_field="should be ignored",  # type: ignore
        )
        assert not hasattr(user, "unknown_field")


class TestUserProfileEndpoint:
    """Tests for /api/users/me endpoint."""

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_get_user_profile_success(self, mock_db, mock_settings):
        """GET /api/users/me should return user profile."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        token = create_test_token(
            user_id="profile-user-456",
            email="profile@example.com",
        )
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "profile-user-456"
        assert data["email"] == "profile@example.com"
        assert "tier" in data
        assert "role" in data
        assert "email_verified" in data

    def test_get_user_profile_no_auth(self):
        """GET /api/users/me without auth should return 401."""
        response = client.get("/api/users/me")
        assert response.status_code == 401

    def test_bearer_scheme_required(self):
        """Auth header must use Bearer scheme."""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        # FastAPI's HTTPBearer returns 403 for wrong scheme
        assert response.status_code in [401, 403]

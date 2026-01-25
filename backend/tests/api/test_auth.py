"""
Tests for JWT authentication middleware.
"""

import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from unittest.mock import patch

from api import app
from api.middleware.auth import decode_token, get_user_from_payload
from api.models.user import TokenPayload

client = TestClient(app)

# Test JWT secret (only for testing)
TEST_JWT_SECRET = "test-secret-key-for-testing-only"


def create_test_token(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    expired: bool = False,
) -> str:
    """Create a test JWT token."""
    now = datetime.now(timezone.utc)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)

    payload = {
        "sub": user_id,
        "email": email,
        "email_confirmed_at": now.isoformat(),
        "aud": "authenticated",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


class TestAuthentication:

    @patch("api.middleware.auth.get_settings")
    def test_valid_token(self, mock_settings):
        """Valid token should decode successfully."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        token = create_test_token()
        payload = decode_token(token)
        assert payload.sub == "test-user-123"
        assert payload.email == "test@example.com"

    @patch("api.middleware.auth.get_settings")
    def test_expired_token(self, mock_settings):
        """Expired token should raise AuthError."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        token = create_test_token(expired=True)
        with pytest.raises(Exception) as exc_info:
            decode_token(token)
        assert "expired" in str(exc_info.value.detail).lower()

    @patch("api.middleware.auth.get_settings")
    def test_invalid_token(self, mock_settings):
        """Invalid token should raise AuthError."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        with pytest.raises(Exception) as exc_info:
            decode_token("invalid-token")
        assert "Invalid token" in str(exc_info.value.detail)

    def test_missing_auth_header(self):
        """Request without auth header should return 401."""
        response = client.get("/api/users/me")
        assert response.status_code == 401

    @patch("api.middleware.auth.get_settings")
    def test_protected_route_with_valid_token(self, mock_settings):
        """Protected route should work with valid token."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        token = create_test_token()
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-user-123"
        assert data["email"] == "test@example.com"

    @patch("api.middleware.auth.get_settings")
    def test_protected_route_with_expired_token(self, mock_settings):
        """Protected route should return 401 with expired token."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        token = create_test_token(expired=True)
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @patch("api.middleware.auth.get_settings")
    def test_missing_jwt_secret(self, mock_settings):
        """Missing JWT secret should return 401."""
        mock_settings.return_value.supabase_jwt_secret = ""
        token = create_test_token()
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert "not configured" in response.json()["detail"].lower()


class TestTokenPayloadConversion:

    def test_get_user_from_payload(self):
        """Should convert payload to AuthenticatedUser."""
        payload = TokenPayload(
            sub="user-123",
            email="test@example.com",
            email_confirmed_at="2024-01-01T00:00:00Z",
            aud="authenticated",
            exp=9999999999,
            iat=1704067200,
        )
        user = get_user_from_payload(payload)
        assert user.id == "user-123"
        assert user.email == "test@example.com"
        assert user.email_verified is True
        assert user.role == "user"
        assert user.tier == "free"

    def test_get_user_from_payload_unverified_email(self):
        """Should handle unverified email correctly."""
        payload = TokenPayload(
            sub="user-456",
            email="unverified@example.com",
            email_confirmed_at=None,
            aud="authenticated",
            exp=9999999999,
            iat=1704067200,
        )
        user = get_user_from_payload(payload)
        assert user.id == "user-456"
        assert user.email == "unverified@example.com"
        assert user.email_verified is False


import os

# Integration test that uses real JWT secret from environment
@pytest.mark.skipif(
    not os.environ.get("PRIZMS_SUPABASE_JWT_SECRET"),
    reason="PRIZMS_SUPABASE_JWT_SECRET not set"
)
class TestAuthIntegration:
    """Integration tests using real Supabase JWT secret from environment."""

    def test_real_jwt_secret_decodes_valid_token(self):
        """Token signed with real JWT secret should decode successfully."""
        secret = os.environ["PRIZMS_SUPABASE_JWT_SECRET"]
        now = datetime.now(timezone.utc)

        # Create a token with the real secret
        payload = {
            "sub": "integration-test-user",
            "email": "integration@test.com",
            "email_confirmed_at": now.isoformat(),
            "aud": "authenticated",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        # Test the full endpoint with real secret (no mocking)
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "integration-test-user"
        assert data["email"] == "integration@test.com"
        assert data["email_verified"] is True

    def test_real_jwt_secret_rejects_wrong_secret(self):
        """Token signed with wrong secret should be rejected."""
        now = datetime.now(timezone.utc)

        # Create a token with a WRONG secret
        payload = {
            "sub": "hacker",
            "email": "hacker@evil.com",
            "aud": "authenticated",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
        }
        wrong_secret = "this-is-not-the-real-secret"
        token = jwt.encode(payload, wrong_secret, algorithm="HS256")

        # Should be rejected
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

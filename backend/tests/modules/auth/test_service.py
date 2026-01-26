import pytest
from unittest.mock import patch, MagicMock
import jwt
from datetime import datetime, timedelta, timezone

from modules.auth.service import AuthService
from modules.auth.exceptions import (
    InvalidTokenError,
    ExpiredTokenError,
    MissingTokenError,
)


class TestAuthService:
    @pytest.fixture
    def service(self):
        """Create auth service with mocked dependencies."""
        with patch("modules.auth.service.get_settings") as mock_settings, \
             patch("modules.auth.service.get_supabase_client") as mock_db:
            mock_settings.return_value.supabase_jwt_secret = "test-secret"
            mock_db.return_value = MagicMock()
            yield AuthService()

    @pytest.fixture
    def valid_token(self):
        """Create a valid JWT token."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "aud": "authenticated",
            "role": "authenticated",
        }
        return jwt.encode(payload, "test-secret", algorithm="HS256")

    @pytest.fixture
    def expired_token(self):
        """Create an expired JWT token."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "aud": "authenticated",
            "role": "authenticated",
        }
        return jwt.encode(payload, "test-secret", algorithm="HS256")

    @pytest.mark.asyncio
    async def test_validate_valid_token(self, service, valid_token):
        """Should validate a valid token and return user."""
        user = await service.validate_token(valid_token)
        assert user.id == "user-123"
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_validate_expired_token(self, service, expired_token):
        """Should raise ExpiredTokenError for expired token."""
        with pytest.raises(ExpiredTokenError):
            await service.validate_token(expired_token)

    @pytest.mark.asyncio
    async def test_validate_invalid_token(self, service):
        """Should raise InvalidTokenError for malformed token."""
        with pytest.raises(InvalidTokenError):
            await service.validate_token("not-a-valid-token")

    @pytest.mark.asyncio
    async def test_validate_missing_token(self, service):
        """Should raise MissingTokenError for empty token."""
        with pytest.raises(MissingTokenError):
            await service.validate_token("")

    @pytest.mark.asyncio
    async def test_validate_none_token(self, service):
        """Should raise MissingTokenError for None token."""
        with pytest.raises(MissingTokenError):
            await service.validate_token(None)

    @pytest.mark.asyncio
    async def test_validate_wrong_secret(self, service):
        """Should raise InvalidTokenError for token signed with wrong secret."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "aud": "authenticated",
            "role": "authenticated",
        }
        wrong_secret_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(InvalidTokenError):
            await service.validate_token(wrong_secret_token)

    @pytest.mark.asyncio
    async def test_validate_wrong_audience(self, service):
        """Should raise InvalidTokenError for token with wrong audience."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "aud": "wrong-audience",
            "role": "authenticated",
        }
        wrong_aud_token = jwt.encode(payload, "test-secret", algorithm="HS256")
        with pytest.raises(InvalidTokenError):
            await service.validate_token(wrong_aud_token)

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_implemented(self, service):
        """get_user_by_id should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await service.get_user_by_id("user-123")

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_implemented(self, service):
        """get_user_by_email should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await service.get_user_by_email("test@example.com")

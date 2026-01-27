"""Tests for usage API endpoints."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from api.app import app
from tests.conftest import create_test_token, TEST_JWT_SECRET


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authorization headers with a valid token."""
    token = create_test_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_usage_service():
    """Create a mock usage service."""
    service = MagicMock()
    
    # Mock get_current_period
    period_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    period_end = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    service.get_current_period.return_value = (period_start, period_end)
    
    # Mock get_user_usage as async
    async def mock_get_user_usage(user_id):
        return {
            "total_tokens": 15000,
            "total_cost": 0.045,
            "debates_count": 3,
        }
    service.get_user_usage = mock_get_user_usage
    
    return service


class TestUsageSummaryEndpoint:
    """Tests for GET /api/usage/summary endpoint."""

    def test_requires_authentication(self, client):
        """Should return 401 without auth token."""
        response = client.get("/api/usage/summary")
        assert response.status_code == 401

    def test_rejects_invalid_token(self, client):
        """Should return 401 with invalid token."""
        from api.middleware.auth import get_current_user
        from fastapi import HTTPException
        
        # Override get_current_user to raise auth error
        async def mock_get_current_user():
            raise HTTPException(status_code=401, detail="Invalid token")
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        try:
            response = client.get(
                "/api/usage/summary",
                headers={"Authorization": "Bearer invalid-token"}
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_rejects_expired_token(self, client):
        """Should return 401 with expired token."""
        from api.middleware.auth import get_current_user
        from fastapi import HTTPException
        
        # Override get_current_user to raise auth error for expired token
        async def mock_get_current_user():
            raise HTTPException(status_code=401, detail="Token has expired")
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        expired_token = create_test_token(expired=True)
        try:
            response = client.get(
                "/api/usage/summary",
                headers={"Authorization": f"Bearer {expired_token}"}
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_returns_usage_summary(self, client, auth_headers, mock_usage_service):
        """Should return usage summary for authenticated user."""
        from modules.usage.service import get_usage_service
        from api.middleware.auth import get_current_user
        from shared.models import AuthenticatedUser
        
        # Override dependencies
        app.dependency_overrides[get_usage_service] = lambda: mock_usage_service
        
        # Create mock user
        mock_user = AuthenticatedUser(
            id="test-user-123",
            email="test@example.com",
            email_verified=True,
            tier="free",
            role="authenticated",
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/api/usage/summary", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "period_start" in data
            assert "period_end" in data
            assert data["total_tokens"] == 15000
            assert data["total_cost"] == 0.045
            assert data["debates_count"] == 3
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_returns_correct_period_dates(self, client, auth_headers, mock_usage_service):
        """Should return correct period dates."""
        from modules.usage.service import get_usage_service
        from api.middleware.auth import get_current_user
        from shared.models import AuthenticatedUser
        
        # Override dependencies
        app.dependency_overrides[get_usage_service] = lambda: mock_usage_service
        
        mock_user = AuthenticatedUser(
            id="test-user-123",
            email="test@example.com",
            email_verified=True,
            tier="free",
            role="authenticated",
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/api/usage/summary", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            # Period should be valid ISO8601 dates
            period_start = datetime.fromisoformat(data["period_start"].replace("Z", "+00:00"))
            period_end = datetime.fromisoformat(data["period_end"].replace("Z", "+00:00"))
            
            assert period_start < period_end
            assert period_start.day == 1
            assert period_end.day == 1
        finally:
            app.dependency_overrides.clear()

    def test_returns_zero_usage_for_new_user(self, client, auth_headers):
        """Should return zero usage for user with no history."""
        from modules.usage.service import get_usage_service, UsageService
        from api.middleware.auth import get_current_user
        from shared.models import AuthenticatedUser
        from modules.usage.pricing import StaticPricingProvider
        
        # Use real service with no data
        service = UsageService(pricing_provider=StaticPricingProvider())
        app.dependency_overrides[get_usage_service] = lambda: service
        
        mock_user = AuthenticatedUser(
            id="new-user-123",
            email="new@example.com",
            email_verified=True,
            tier="free",
            role="authenticated",
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/api/usage/summary", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_tokens"] == 0
            assert data["total_cost"] == 0.0
            assert data["debates_count"] == 0
        finally:
            app.dependency_overrides.clear()

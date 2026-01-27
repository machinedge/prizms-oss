"""
Tests for debate API endpoints.

Tests the REST endpoints for debate CRUD operations.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from decimal import Decimal

from api.app import create_app
from api.dependencies import get_debate_service
from modules.debates.models import (
    DebateStatus,
    Debate,
    DebateSettings,
    DebateListResponse,
    DebateListItem,
)
from modules.debates.exceptions import DebateNotFoundError, DebateAccessDeniedError

# Import shared test utilities
from tests.conftest import TEST_JWT_SECRET, create_test_token


@pytest.fixture
def app():
    """Create a fresh app for each test."""
    return create_app()


@pytest.fixture
def mock_debate() -> Debate:
    """Create a mock debate for testing."""
    return Debate(
        id="debate-123",
        user_id="test-user-123",
        question="What is AI?",
        status=DebateStatus.PENDING,
        provider="anthropic",
        model="claude-3-sonnet",
        settings=DebateSettings(),
        max_rounds=3,
        current_round=0,
        total_input_tokens=0,
        total_output_tokens=0,
        total_cost=Decimal(0),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_debate_list() -> DebateListResponse:
    """Create a mock debate list response."""
    return DebateListResponse(
        debates=[
            DebateListItem(
                id="debate-123",
                question="What is AI?",
                status=DebateStatus.PENDING,
                provider="anthropic",
                model="claude-3-sonnet",
                current_round=0,
                max_rounds=3,
                total_cost=Decimal(0),
                created_at=datetime.now(timezone.utc),
            )
        ],
        total=1,
        page=1,
        page_size=20,
        has_more=False,
    )


class TestCreateDebate:
    """Tests for POST /api/debates"""

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_create_debate_success(
        self, mock_db, mock_settings, app, mock_debate
    ):
        """Should create a new debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.create_debate.return_value = mock_debate
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.post(
            "/api/debates",
            json={
                "question": "What is AI?",
                "provider": "anthropic",
                "model": "claude-3-sonnet",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "debate-123"
        assert data["status"] == "pending"
        assert data["question"] == "What is AI?"

        # Cleanup
        app.dependency_overrides.clear()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_create_debate_with_settings(
        self, mock_db, mock_settings, app, mock_debate
    ):
        """Should create a debate with custom settings."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        custom_debate = mock_debate.model_copy(
            update={
                "settings": DebateSettings(max_rounds=5, temperature=0.9),
                "max_rounds": 5,
            }
        )

        mock_service = AsyncMock()
        mock_service.create_debate.return_value = custom_debate
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.post(
            "/api/debates",
            json={
                "question": "What is AI?",
                "provider": "anthropic",
                "model": "claude-3-sonnet",
                "settings": {"max_rounds": 5, "temperature": 0.9},
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["max_rounds"] == 5

        app.dependency_overrides.clear()

    def test_create_debate_unauthorized(self, app):
        """Should reject unauthenticated requests."""
        client = TestClient(app)
        response = client.post(
            "/api/debates",
            json={
                "question": "What is AI?",
                "provider": "anthropic",
                "model": "claude-3-sonnet",
            },
        )
        assert response.status_code == 401

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_create_debate_invalid_request(self, mock_db, mock_settings, app):
        """Should reject invalid request body."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.post(
            "/api/debates",
            json={"question": ""},  # Missing required fields
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

        app.dependency_overrides.clear()


class TestListDebates:
    """Tests for GET /api/debates"""

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_list_debates_success(
        self, mock_db, mock_settings, app, mock_debate_list
    ):
        """Should list user's debates."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.list_debates.return_value = mock_debate_list
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.get(
            "/api/debates",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "debates" in data
        assert data["total"] == 1
        assert len(data["debates"]) == 1

        app.dependency_overrides.clear()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_list_debates_with_pagination(
        self, mock_db, mock_settings, app, mock_debate_list
    ):
        """Should support pagination parameters."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.list_debates.return_value = mock_debate_list
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.get(
            "/api/debates?page=2&page_size=10",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        mock_service.list_debates.assert_called_once_with(
            "test-user-123", 2, 10, None
        )

        app.dependency_overrides.clear()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_list_debates_with_status_filter(
        self, mock_db, mock_settings, app, mock_debate_list
    ):
        """Should support status filter."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.list_debates.return_value = mock_debate_list
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.get(
            "/api/debates?status=completed",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        mock_service.list_debates.assert_called_once_with(
            "test-user-123", 1, 20, DebateStatus.COMPLETED
        )

        app.dependency_overrides.clear()

    def test_list_debates_unauthorized(self, app):
        """Should reject unauthenticated requests."""
        client = TestClient(app)
        response = client.get("/api/debates")
        assert response.status_code == 401


class TestGetDebate:
    """Tests for GET /api/debates/{debate_id}"""

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_get_debate_success(
        self, mock_db, mock_settings, app, mock_debate
    ):
        """Should get a debate by ID."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.get_debate.return_value = mock_debate
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.get(
            "/api/debates/debate-123",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "debate-123"

        app.dependency_overrides.clear()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_get_debate_not_found(
        self, mock_db, mock_settings, app
    ):
        """Should return 404 for non-existent debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.get_debate.return_value = None
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.get(
            "/api/debates/non-existent",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_get_debate_access_denied(
        self, mock_db, mock_settings, app
    ):
        """Should return 404 for other user's debate (not 403 for security)."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.get_debate.side_effect = DebateAccessDeniedError(
            "debate-123", "test-user-123"
        )
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.get(
            "/api/debates/debate-123",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Returns 404 to avoid leaking information about debate existence
        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_get_debate_unauthorized(self, app):
        """Should reject unauthenticated requests."""
        client = TestClient(app)
        response = client.get("/api/debates/debate-123")
        assert response.status_code == 401


class TestCancelDebate:
    """Tests for POST /api/debates/{debate_id}/cancel"""

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_cancel_debate_success(
        self, mock_db, mock_settings, app, mock_debate
    ):
        """Should cancel a debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        cancelled_debate = mock_debate.model_copy(
            update={"status": DebateStatus.CANCELLED}
        )

        mock_service = AsyncMock()
        mock_service.cancel_debate.return_value = cancelled_debate
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.post(
            "/api/debates/debate-123/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        app.dependency_overrides.clear()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_cancel_debate_not_found(
        self, mock_db, mock_settings, app
    ):
        """Should return 404 for non-existent debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.cancel_debate.side_effect = DebateNotFoundError("non-existent")
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.post(
            "/api/debates/non-existent/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_cancel_debate_unauthorized(self, app):
        """Should reject unauthenticated requests."""
        client = TestClient(app)
        response = client.post("/api/debates/debate-123/cancel")
        assert response.status_code == 401


class TestDeleteDebate:
    """Tests for DELETE /api/debates/{debate_id}"""

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_delete_debate_success(
        self, mock_db, mock_settings, app
    ):
        """Should delete a debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.delete_debate.return_value = True
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.delete(
            "/api/debates/debate-123",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        app.dependency_overrides.clear()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_delete_debate_not_found(
        self, mock_db, mock_settings, app
    ):
        """Should return 404 for non-existent debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.delete_debate.side_effect = DebateNotFoundError("non-existent")
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.delete(
            "/api/debates/non-existent",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    @patch("modules.auth.service.get_settings")
    @patch("modules.auth.service.get_supabase_client")
    def test_delete_debate_access_denied(
        self, mock_db, mock_settings, app
    ):
        """Should return 404 for other user's debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET
        mock_db.return_value = MagicMock()

        mock_service = AsyncMock()
        mock_service.delete_debate.side_effect = DebateAccessDeniedError(
            "debate-123", "test-user-123"
        )
        app.dependency_overrides[get_debate_service] = lambda: mock_service

        client = TestClient(app)
        token = create_test_token()
        response = client.delete(
            "/api/debates/debate-123",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_delete_debate_unauthorized(self, app):
        """Should reject unauthenticated requests."""
        client = TestClient(app)
        response = client.delete("/api/debates/debate-123")
        assert response.status_code == 401

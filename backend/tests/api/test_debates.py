"""
Tests for Debate API endpoints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api import app
from api.models.debate import DebateStatus

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


class TestDebateEndpoints:

    @patch("api.middleware.auth.get_settings")
    @patch("api.services.debates.get_supabase_client")
    def test_create_debate(self, mock_db, mock_settings):
        """Should create a new debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET

        # Mock the database insert
        mock_table = MagicMock()
        mock_db.return_value.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value.data = [{
            "id": "debate-123",
            "question": "Test question",
            "status": "pending",
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "max_rounds": 3,
            "current_round": 0,
            "total_tokens": 0,
            "total_cost": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }]

        token = create_test_token()
        response = client.post(
            "/api/debates",
            json={
                "question": "Test question",
                "provider": "anthropic",
                "model": "claude-3-sonnet",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["question"] == "Test question"
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-3-sonnet"

    @patch("api.middleware.auth.get_settings")
    @patch("api.services.debates.get_supabase_client")
    def test_list_debates(self, mock_db, mock_settings):
        """Should list user's debates."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET

        # Mock the database queries
        mock_table = MagicMock()
        mock_db.return_value.table.return_value = mock_table

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.count = 1
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_count_result

        # Mock data query
        mock_data_result = MagicMock()
        mock_data_result.data = [{
            "id": "debate-123",
            "question": "Test question",
            "status": "completed",
            "provider": "anthropic",
            "model": "claude",
            "current_round": 3,
            "max_rounds": 3,
            "total_cost": 0.05,
            "created_at": "2024-01-01T00:00:00Z",
        }]
        mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_data_result

        token = create_test_token()
        response = client.get(
            "/api/debates",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "debates" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "has_more" in data

    @patch("api.middleware.auth.get_settings")
    @patch("api.services.debates.get_supabase_client")
    def test_get_debate(self, mock_db, mock_settings):
        """Should get a specific debate with rounds."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET

        # Mock the database queries
        mock_table = MagicMock()
        mock_db.return_value.table.return_value = mock_table

        # Mock debate query
        mock_debate_result = MagicMock()
        mock_debate_result.data = [{
            "id": "debate-123",
            "question": "Test question",
            "status": "completed",
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "max_rounds": 3,
            "current_round": 3,
            "total_tokens": 1000,
            "total_cost": 0.05,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T01:00:00Z",
            "completed_at": "2024-01-01T01:00:00Z",
        }]

        # Mock rounds query
        mock_rounds_result = MagicMock()
        mock_rounds_result.data = [{
            "id": "round-1",
            "round_number": 1,
            "created_at": "2024-01-01T00:10:00Z",
            "debate_responses": [{
                "personality_name": "critic",
                "thinking_content": "thinking...",
                "answer_content": "answer...",
                "tokens_used": 100,
                "cost": 0.01,
            }],
        }]

        # Mock synthesis query
        mock_synthesis_result = MagicMock()
        mock_synthesis_result.data = [{
            "content": "Final synthesis content",
            "tokens_used": 200,
            "cost": 0.02,
            "created_at": "2024-01-01T01:00:00Z",
        }]

        # Set up the mock chain for different table calls
        def table_side_effect(table_name):
            mock = MagicMock()
            if table_name == "debates":
                mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_debate_result
            elif table_name == "debate_rounds":
                mock.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_rounds_result
            elif table_name == "debate_synthesis":
                mock.select.return_value.eq.return_value.execute.return_value = mock_synthesis_result
            return mock

        mock_db.return_value.table.side_effect = table_side_effect

        token = create_test_token()
        response = client.get(
            "/api/debates/debate-123",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "debate-123"
        assert data["status"] == "completed"
        assert len(data["rounds"]) == 1
        assert data["synthesis"] is not None
        assert data["synthesis"]["content"] == "Final synthesis content"

    @patch("api.middleware.auth.get_settings")
    @patch("api.services.debates.get_supabase_client")
    def test_get_debate_not_found(self, mock_db, mock_settings):
        """Should return 404 for non-existent debate."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET

        # Mock the database query to return empty
        mock_table = MagicMock()
        mock_db.return_value.table.return_value = mock_table
        mock_result = MagicMock()
        mock_result.data = []
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        token = create_test_token()
        response = client.get(
            "/api/debates/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Debate not found"

    def test_create_debate_unauthorized(self):
        """Should reject unauthenticated requests."""
        response = client.post(
            "/api/debates",
            json={
                "question": "Test question",
                "provider": "anthropic",
                "model": "claude-3-sonnet",
            },
        )
        assert response.status_code == 401

    def test_list_debates_unauthorized(self):
        """Should reject unauthenticated list requests."""
        response = client.get("/api/debates")
        assert response.status_code == 401

    def test_get_debate_unauthorized(self):
        """Should reject unauthenticated get requests."""
        response = client.get("/api/debates/some-id")
        assert response.status_code == 401

    @patch("api.middleware.auth.get_settings")
    @patch("api.services.debates.get_supabase_client")
    def test_create_debate_validation_error(self, mock_db, mock_settings):
        """Should return 422 for invalid input."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET

        token = create_test_token()
        # Missing required fields
        response = client.post(
            "/api/debates",
            json={"question": "Test"},  # Missing provider and model
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    @patch("api.middleware.auth.get_settings")
    @patch("api.services.debates.get_supabase_client")
    def test_create_debate_empty_question(self, mock_db, mock_settings):
        """Should reject empty question."""
        mock_settings.return_value.supabase_jwt_secret = TEST_JWT_SECRET

        token = create_test_token()
        response = client.post(
            "/api/debates",
            json={
                "question": "",
                "provider": "anthropic",
                "model": "claude-3-sonnet",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


class TestDebateModels:
    """Tests for debate Pydantic models."""

    def test_debate_status_enum(self):
        """Should have correct status values."""
        assert DebateStatus.PENDING.value == "pending"
        assert DebateStatus.ACTIVE.value == "active"
        assert DebateStatus.COMPLETED.value == "completed"
        assert DebateStatus.FAILED.value == "failed"

    def test_create_debate_request_defaults(self):
        """Should have correct default settings."""
        from api.models.debate import CreateDebateRequest, DebateSettings

        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        assert request.settings.max_rounds == 3
        assert request.settings.temperature == 0.7

    def test_debate_settings_validation(self):
        """Should validate settings bounds."""
        from api.models.debate import DebateSettings

        # Valid settings
        settings = DebateSettings(max_rounds=5, temperature=1.0)
        assert settings.max_rounds == 5

        # Invalid max_rounds
        with pytest.raises(Exception):
            DebateSettings(max_rounds=0)

        with pytest.raises(Exception):
            DebateSettings(max_rounds=11)

        # Invalid temperature
        with pytest.raises(Exception):
            DebateSettings(temperature=-0.1)

        with pytest.raises(Exception):
            DebateSettings(temperature=2.5)

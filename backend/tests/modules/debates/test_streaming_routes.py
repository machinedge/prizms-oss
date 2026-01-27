"""Tests for the debates SSE streaming endpoint."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.app import app
from api.middleware.auth import get_current_user
from api.dependencies import get_debate_service
from shared.models import AuthenticatedUser
from modules.debates.models import (
    DebateEvent,
    DebateEventType,
    DebateStatus,
)


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return AuthenticatedUser(
        id="user-123",
        email="test@example.com",
    )


@pytest.fixture
def client_with_auth(mock_user):
    """Create a test client with mocked authentication."""

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestStreamDebateEndpoint:
    """Tests for the GET /api/debates/{id}/stream endpoint."""

    def test_requires_authentication(self):
        """Should require authentication."""
        client = TestClient(app)
        # Without auth header, should get 401 or 403
        response = client.get("/api/debates/debate-123/stream")
        # FastAPI will return 401 or raise an error without proper auth
        assert response.status_code in [401, 403, 422]

    def test_returns_sse_content_type(self, client_with_auth, mock_user):
        """Should return text/event-stream content type."""

        async def mock_stream(*args, **kwargs):
            yield DebateEvent(
                type=DebateEventType.DEBATE_STARTED,
                debate_id="debate-123",
            )
            yield DebateEvent(
                type=DebateEventType.DEBATE_COMPLETED,
                debate_id="debate-123",
            )

        mock_service = MagicMock()
        mock_service.start_debate_stream = mock_stream

        app.dependency_overrides[get_debate_service] = lambda: mock_service

        try:
            with client_with_auth.stream("GET", "/api/debates/debate-123/stream") as response:
                assert response.status_code == 200
                content_type = response.headers.get("content-type", "")
                assert "text/event-stream" in content_type
        finally:
            del app.dependency_overrides[get_debate_service]

    def test_streams_debate_events(self, client_with_auth, mock_user):
        """Should stream debate events."""

        async def mock_stream(*args, **kwargs):
            yield DebateEvent(
                type=DebateEventType.DEBATE_STARTED,
                debate_id="debate-123",
                progress={"question": "Test?"},
            )
            yield DebateEvent(
                type=DebateEventType.DEBATE_COMPLETED,
                debate_id="debate-123",
            )

        mock_service = MagicMock()
        mock_service.start_debate_stream = mock_stream

        app.dependency_overrides[get_debate_service] = lambda: mock_service

        try:
            with client_with_auth.stream("GET", "/api/debates/debate-123/stream") as response:
                assert response.status_code == 200

                # Read and parse events
                events = []
                for line in response.iter_lines():
                    if line.startswith("event:"):
                        events.append(line)

                # Should have at least started and completed events
                assert len(events) >= 2
        finally:
            del app.dependency_overrides[get_debate_service]

    def test_handles_error_event(self, client_with_auth, mock_user):
        """Should handle error events gracefully."""

        async def mock_stream(*args, **kwargs):
            yield DebateEvent(
                type=DebateEventType.ERROR,
                debate_id="debate-123",
                error="Debate not found",
            )

        mock_service = MagicMock()
        mock_service.start_debate_stream = mock_stream

        app.dependency_overrides[get_debate_service] = lambda: mock_service

        try:
            with client_with_auth.stream("GET", "/api/debates/debate-123/stream") as response:
                assert response.status_code == 200

                # Should receive the error event
                found_error = False
                for line in response.iter_lines():
                    if "error" in line.lower():
                        found_error = True
                        break

                assert found_error
        finally:
            del app.dependency_overrides[get_debate_service]

    def test_returns_error_for_non_pending_debate(self, client_with_auth, mock_user):
        """Should return error event for non-pending debate."""

        async def mock_stream(*args, **kwargs):
            yield DebateEvent(
                type=DebateEventType.ERROR,
                debate_id="debate-123",
                error="Debate already completed",
            )

        mock_service = MagicMock()
        mock_service.start_debate_stream = mock_stream

        app.dependency_overrides[get_debate_service] = lambda: mock_service

        try:
            with client_with_auth.stream("GET", "/api/debates/debate-123/stream") as response:
                assert response.status_code == 200

                # Consume the stream
                content = b"".join(response.iter_bytes())
                assert b"error" in content.lower() or b"ERROR" in content
        finally:
            del app.dependency_overrides[get_debate_service]


class TestEventGenerator:
    """Tests for the event_generator function."""

    @pytest.mark.asyncio
    async def test_yields_correct_event_format(self):
        """Should yield events in SSE format."""
        from modules.debates.routes import event_generator

        async def mock_stream(*args, **kwargs):
            yield DebateEvent(
                type=DebateEventType.DEBATE_STARTED,
                debate_id="debate-123",
            )

        mock_service = MagicMock()
        mock_service.start_debate_stream = mock_stream

        events = []
        async for event in event_generator("debate-123", "user-123", mock_service):
            events.append(event)

        assert len(events) == 1
        assert events[0]["event"] == "debate_started"
        assert "data" in events[0]

    @pytest.mark.asyncio
    async def test_excludes_none_fields_from_data(self):
        """Should exclude None fields from event data."""
        from modules.debates.routes import event_generator

        async def mock_stream(*args, **kwargs):
            yield DebateEvent(
                type=DebateEventType.DEBATE_STARTED,
                debate_id="debate-123",
                # These should be excluded:
                round_number=None,
                personality=None,
                content=None,
            )

        mock_service = MagicMock()
        mock_service.start_debate_stream = mock_stream

        events = []
        async for event in event_generator("debate-123", "user-123", mock_service):
            events.append(event)

        data = events[0]["data"]
        # None fields should not appear in the JSON
        assert "round_number" not in data or "null" not in data

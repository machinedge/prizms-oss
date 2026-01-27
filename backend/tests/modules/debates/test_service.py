"""Tests for debates service with Supabase."""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone
from decimal import Decimal

from modules.debates.service import DebateService, get_debate_service, reset_debate_service
from modules.debates.models import (
    CreateDebateRequest,
    DebateStatus,
    DebateSettings,
    DebateEventType,
)
from modules.debates.exceptions import DebateNotFoundError, DebateAccessDeniedError


def create_mock_debate_data(
    debate_id: str = "debate-123",
    user_id: str = "user-123",
    question: str = "Test question",
    status: str = "pending",
) -> dict:
    """Helper to create mock debate data."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": debate_id,
        "user_id": user_id,
        "question": question,
        "status": status,
        "provider": "anthropic",
        "model": "claude-3-5-sonnet",
        "max_rounds": 3,
        "current_round": 0,
        "settings": {
            "max_rounds": 3,
            "temperature": 0.7,
            "personalities": ["optimist", "pessimist", "analyst"],
            "include_synthesis": True,
        },
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost": "0",
        "created_at": now,
        "updated_at": now,
    }


def create_supabase_mock():
    """Create a properly configured Supabase mock."""
    mock = MagicMock()
    
    # Create separate table mocks to handle different queries
    def table_handler(table_name):
        table_mock = MagicMock()
        table_mock._table_name = table_name
        return table_mock
    
    mock.table.side_effect = table_handler
    return mock


@pytest.fixture(autouse=True)
def reset_service_singleton():
    """Reset the service singleton before each test."""
    reset_debate_service()
    yield
    reset_debate_service()


class TestDebateService:
    @pytest.mark.asyncio
    async def test_create_debate(self):
        """Should create a debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        # Setup mock response for insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            create_mock_debate_data()
        ]

        request = CreateDebateRequest(
            question="Test question",
            provider="anthropic",
            model="claude-3-5-sonnet",
        )
        debate = await service.create_debate("user-123", request)

        assert debate.id == "debate-123"
        assert debate.status == DebateStatus.PENDING
        assert debate.user_id == "user-123"
        assert debate.question == "Test question"
        assert debate.provider == "anthropic"
        assert debate.model == "claude-3-5-sonnet"
        assert debate.current_round == 0
        assert debate.max_rounds == 3

    @pytest.mark.asyncio
    async def test_create_debate_with_custom_settings(self):
        """Should create a debate with custom settings."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {
                **create_mock_debate_data(),
                "max_rounds": 5,
                "settings": {
                    "max_rounds": 5,
                    "temperature": 0.9,
                    "personalities": ["optimist", "pessimist"],
                    "include_synthesis": True,
                },
            }
        ]

        request = CreateDebateRequest(
            question="Custom settings test",
            provider="openai",
            model="gpt-4",
            settings=DebateSettings(
                max_rounds=5,
                temperature=0.9,
                personalities=["optimist", "pessimist"],
            ),
        )
        debate = await service.create_debate("user-123", request)

        assert debate.max_rounds == 5
        assert debate.settings.temperature == 0.9
        assert len(debate.settings.personalities) == 2

    @pytest.mark.asyncio
    async def test_get_debate(self):
        """Should get a debate by ID."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        debate_data = create_mock_debate_data()
        
        # Configure mock for chained calls
        debates_table = MagicMock()
        rounds_table = MagicMock()
        synthesis_table = MagicMock()
        
        def table_router(name):
            if name == "debates":
                return debates_table
            elif name == "debate_rounds":
                return rounds_table
            elif name == "debate_synthesis":
                return synthesis_table
            return MagicMock()
        
        mock_supabase.table.side_effect = table_router
        
        # Debates query
        debates_table.select.return_value.eq.return_value.execute.return_value.data = [debate_data]
        
        # Rounds query (empty)
        rounds_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        
        # Synthesis query (empty)
        synthesis_table.select.return_value.eq.return_value.execute.return_value.data = []

        fetched = await service.get_debate("debate-123", "user-123")

        assert fetched is not None
        assert fetched.id == "debate-123"
        assert fetched.question == "Test question"

    @pytest.mark.asyncio
    async def test_get_debate_not_found(self):
        """Should return None for non-existent debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        result = await service.get_debate("non-existent-id", "user-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_debate_wrong_user(self):
        """Should deny access to other user's debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        debate_data = create_mock_debate_data(user_id="user-123")
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [debate_data]

        with pytest.raises(DebateAccessDeniedError) as exc_info:
            await service.get_debate("debate-123", "other-user")
        
        assert exc_info.value.code == "DEBATE_ACCESS_DENIED"
        assert exc_info.value.details["debate_id"] == "debate-123"
        assert exc_info.value.details["user_id"] == "other-user"

    @pytest.mark.asyncio
    async def test_list_debates(self):
        """Should list user's debates."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Mock count result
        count_result = MagicMock()
        count_result.count = 2
        
        # Mock data result
        data_result = MagicMock()
        data_result.data = [
            {
                "id": "debate-1",
                "question": "Test 1",
                "status": "pending",
                "provider": "anthropic",
                "model": "claude",
                "max_rounds": 3,
                "current_round": 0,
                "total_cost": "0",
                "created_at": now,
            },
            {
                "id": "debate-2",
                "question": "Test 2",
                "status": "pending",
                "provider": "anthropic",
                "model": "claude",
                "max_rounds": 3,
                "current_round": 0,
                "total_cost": "0",
                "created_at": now,
            },
        ]
        
        # Return count first, then data
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = count_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = data_result

        response = await service.list_debates("user-123")
        assert response.total == 2
        assert len(response.debates) == 2
        assert response.page == 1
        assert response.has_more is False

    @pytest.mark.asyncio
    async def test_list_debates_pagination(self):
        """Should paginate debate list."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        now = datetime.now(timezone.utc).isoformat()
        
        count_result = MagicMock()
        count_result.count = 3
        
        data_result = MagicMock()
        data_result.data = [
            {
                "id": "debate-1",
                "question": "Test 1",
                "status": "pending",
                "provider": "anthropic",
                "model": "claude",
                "max_rounds": 3,
                "current_round": 0,
                "total_cost": "0",
                "created_at": now,
            },
            {
                "id": "debate-2",
                "question": "Test 2",
                "status": "pending",
                "provider": "anthropic",
                "model": "claude",
                "max_rounds": 3,
                "current_round": 0,
                "total_cost": "0",
                "created_at": now,
            },
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = count_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = data_result

        response = await service.list_debates("user-123", page=1, page_size=2)
        assert response.total == 3
        assert len(response.debates) == 2
        assert response.has_more is True

    @pytest.mark.asyncio
    async def test_list_debates_filter_by_status(self):
        """Should filter debates by status."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        now = datetime.now(timezone.utc).isoformat()
        
        count_result = MagicMock()
        count_result.count = 1
        
        data_result = MagicMock()
        data_result.data = [
            {
                "id": "debate-1",
                "question": "Test 1",
                "status": "pending",
                "provider": "anthropic",
                "model": "claude",
                "max_rounds": 3,
                "current_round": 0,
                "total_cost": "0",
                "created_at": now,
            },
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = count_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = data_result

        response = await service.list_debates("user-123", status=DebateStatus.PENDING)
        assert response.page == 1

    @pytest.mark.asyncio
    async def test_list_debates_truncates_long_questions(self):
        """Should truncate long questions in list items."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        now = datetime.now(timezone.utc).isoformat()
        long_question = "a" * 150
        
        count_result = MagicMock()
        count_result.count = 1
        
        data_result = MagicMock()
        data_result.data = [
            {
                "id": "debate-1",
                "question": long_question,
                "status": "pending",
                "provider": "anthropic",
                "model": "claude",
                "max_rounds": 3,
                "current_round": 0,
                "total_cost": "0",
                "created_at": now,
            },
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = count_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = data_result

        response = await service.list_debates("user-123")
        assert len(response.debates[0].question) == 103  # 100 + "..."
        assert response.debates[0].question.endswith("...")

    @pytest.mark.asyncio
    async def test_start_debate_stream_not_found(self):
        """Should yield error event for non-existent debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        events = []
        async for event in service.start_debate_stream("non-existent", "user-123"):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == DebateEventType.ERROR
        assert "not found" in events[0].error.lower()

    @pytest.mark.asyncio
    async def test_start_debate_stream_already_completed(self):
        """Should yield error event for non-pending debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        debate_data = create_mock_debate_data(status="completed")
        
        # Configure mock for chained calls
        debates_table = MagicMock()
        rounds_table = MagicMock()
        synthesis_table = MagicMock()
        
        def table_router(name):
            if name == "debates":
                return debates_table
            elif name == "debate_rounds":
                return rounds_table
            elif name == "debate_synthesis":
                return synthesis_table
            return MagicMock()
        
        mock_supabase.table.side_effect = table_router
        
        # Debates query
        debates_table.select.return_value.eq.return_value.execute.return_value.data = [debate_data]
        
        # Rounds query (empty)
        rounds_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        
        # Synthesis query (empty)
        synthesis_table.select.return_value.eq.return_value.execute.return_value.data = []

        events = []
        async for event in service.start_debate_stream("debate-123", "user-123"):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == DebateEventType.ERROR
        assert "already completed" in events[0].error.lower()

    @pytest.mark.asyncio
    async def test_cancel_debate(self):
        """Should cancel a debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        debate_data = create_mock_debate_data()
        cancelled_data = {**debate_data, "status": "cancelled"}
        
        # Configure mock for chained calls
        debates_table = MagicMock()
        rounds_table = MagicMock()
        synthesis_table = MagicMock()
        
        call_count = [0]
        
        def table_router(name):
            if name == "debates":
                return debates_table
            elif name == "debate_rounds":
                return rounds_table
            elif name == "debate_synthesis":
                return synthesis_table
            return MagicMock()
        
        mock_supabase.table.side_effect = table_router
        
        # First call returns original, after cancel returns cancelled
        def get_debate_data():
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] <= 1:
                result.data = [debate_data]
            else:
                result.data = [cancelled_data]
            return result
        
        debates_table.select.return_value.eq.return_value.execute.side_effect = get_debate_data
        debates_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        rounds_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        synthesis_table.select.return_value.eq.return_value.execute.return_value.data = []

        cancelled = await service.cancel_debate("debate-123", "user-123")

        assert cancelled.status == DebateStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_debate_not_found(self):
        """Should raise error for non-existent debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(DebateNotFoundError):
            await service.cancel_debate("non-existent", "user-123")

    @pytest.mark.asyncio
    async def test_cancel_debate_wrong_user(self):
        """Should deny cancelling other user's debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        debate_data = create_mock_debate_data(user_id="user-123")
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [debate_data]

        with pytest.raises(DebateAccessDeniedError):
            await service.cancel_debate("debate-123", "other-user")

    @pytest.mark.asyncio
    async def test_delete_debate(self):
        """Should delete a debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        debate_data = create_mock_debate_data()
        
        # Configure mock for chained calls
        debates_table = MagicMock()
        rounds_table = MagicMock()
        synthesis_table = MagicMock()
        
        def table_router(name):
            if name == "debates":
                return debates_table
            elif name == "debate_rounds":
                return rounds_table
            elif name == "debate_synthesis":
                return synthesis_table
            return MagicMock()
        
        mock_supabase.table.side_effect = table_router
        
        debates_table.select.return_value.eq.return_value.execute.return_value.data = [debate_data]
        debates_table.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        
        rounds_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        synthesis_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = await service.delete_debate("debate-123", "user-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_debate_not_found(self):
        """Should raise error for non-existent debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(DebateNotFoundError):
            await service.delete_debate("non-existent", "user-123")

    @pytest.mark.asyncio
    async def test_delete_debate_wrong_user(self):
        """Should deny deleting other user's debate."""
        mock_supabase = MagicMock()
        service = DebateService(supabase_client=mock_supabase)
        
        debate_data = create_mock_debate_data(user_id="user-123")
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [debate_data]

        with pytest.raises(DebateAccessDeniedError):
            await service.delete_debate("debate-123", "other-user")


class TestGetDebateService:
    @patch("shared.database.get_supabase_client")
    def test_get_debate_service_returns_singleton(self, mock_get_client):
        """Should return the same instance."""
        mock_get_client.return_value = MagicMock()

        service1 = get_debate_service()
        service2 = get_debate_service()

        assert service1 is service2

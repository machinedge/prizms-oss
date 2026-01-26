"""Tests for debates service."""

import pytest
from datetime import datetime, timezone

from modules.debates.service import DebateService, get_debate_service
from modules.debates.models import (
    CreateDebateRequest,
    DebateStatus,
    DebateSettings,
    DebateEventType,
)
from modules.debates.exceptions import DebateNotFoundError, DebateAccessDeniedError


class TestDebateService:
    @pytest.fixture
    def service(self):
        """Create debate service."""
        return DebateService()

    @pytest.mark.asyncio
    async def test_create_debate(self, service):
        """Should create a debate."""
        request = CreateDebateRequest(
            question="Test question",
            provider="anthropic",
            model="claude-3-5-sonnet",
        )
        debate = await service.create_debate("user-123", request)

        assert debate.id is not None
        assert debate.status == DebateStatus.PENDING
        assert debate.user_id == "user-123"
        assert debate.question == "Test question"
        assert debate.provider == "anthropic"
        assert debate.model == "claude-3-5-sonnet"
        assert debate.current_round == 0
        assert debate.max_rounds == 3

    @pytest.mark.asyncio
    async def test_create_debate_with_custom_settings(self, service):
        """Should create a debate with custom settings."""
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
    async def test_get_debate(self, service):
        """Should get a debate by ID."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        created = await service.create_debate("user-123", request)
        fetched = await service.get_debate(created.id, "user-123")

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.question == "Test"

    @pytest.mark.asyncio
    async def test_get_debate_not_found(self, service):
        """Should return None for non-existent debate."""
        result = await service.get_debate("non-existent-id", "user-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_debate_wrong_user(self, service):
        """Should deny access to other user's debate."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        debate = await service.create_debate("user-123", request)

        with pytest.raises(DebateAccessDeniedError) as exc_info:
            await service.get_debate(debate.id, "other-user")
        
        assert exc_info.value.code == "DEBATE_ACCESS_DENIED"
        assert exc_info.value.details["debate_id"] == debate.id
        assert exc_info.value.details["user_id"] == "other-user"

    @pytest.mark.asyncio
    async def test_list_debates(self, service):
        """Should list user's debates."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        await service.create_debate("user-123", request)
        await service.create_debate("user-123", request)

        response = await service.list_debates("user-123")
        assert response.total == 2
        assert len(response.debates) == 2
        assert response.page == 1
        assert response.has_more is False

    @pytest.mark.asyncio
    async def test_list_debates_pagination(self, service):
        """Should paginate debate list."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        # Create 3 debates
        for _ in range(3):
            await service.create_debate("user-123", request)

        # Get first page with page_size=2
        response = await service.list_debates("user-123", page=1, page_size=2)
        assert response.total == 3
        assert len(response.debates) == 2
        assert response.has_more is True

        # Get second page
        response = await service.list_debates("user-123", page=2, page_size=2)
        assert len(response.debates) == 1
        assert response.has_more is False

    @pytest.mark.asyncio
    async def test_list_debates_filter_by_status(self, service):
        """Should filter debates by status."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        await service.create_debate("user-123", request)
        await service.create_debate("user-123", request)

        # Both are PENDING
        response = await service.list_debates("user-123", status=DebateStatus.PENDING)
        assert response.total == 2

        # None are COMPLETED
        response = await service.list_debates("user-123", status=DebateStatus.COMPLETED)
        assert response.total == 0

    @pytest.mark.asyncio
    async def test_list_debates_only_own(self, service):
        """Should only list user's own debates."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        await service.create_debate("user-123", request)
        await service.create_debate("user-456", request)

        response = await service.list_debates("user-123")
        assert response.total == 1

    @pytest.mark.asyncio
    async def test_list_debates_truncates_long_questions(self, service):
        """Should truncate long questions in list items."""
        long_question = "a" * 150
        request = CreateDebateRequest(
            question=long_question,
            provider="anthropic",
            model="claude",
        )
        await service.create_debate("user-123", request)

        response = await service.list_debates("user-123")
        assert len(response.debates[0].question) == 103  # 100 + "..."
        assert response.debates[0].question.endswith("...")

    @pytest.mark.asyncio
    async def test_start_debate_stream(self, service):
        """Should stream debate events."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        debate = await service.create_debate("user-123", request)

        events = []
        async for event in service.start_debate_stream(debate.id, "user-123"):
            events.append(event)

        assert len(events) >= 2
        assert events[0].type == DebateEventType.DEBATE_STARTED
        assert events[-1].type == DebateEventType.DEBATE_COMPLETED

    @pytest.mark.asyncio
    async def test_start_debate_stream_not_found(self, service):
        """Should raise error for non-existent debate."""
        with pytest.raises(DebateNotFoundError):
            async for _ in service.start_debate_stream("non-existent", "user-123"):
                pass

    @pytest.mark.asyncio
    async def test_cancel_debate(self, service):
        """Should cancel a debate."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        debate = await service.create_debate("user-123", request)
        cancelled = await service.cancel_debate(debate.id, "user-123")

        assert cancelled.status == DebateStatus.CANCELLED
        assert cancelled.updated_at > debate.updated_at

    @pytest.mark.asyncio
    async def test_cancel_debate_not_found(self, service):
        """Should raise error for non-existent debate."""
        with pytest.raises(DebateNotFoundError):
            await service.cancel_debate("non-existent", "user-123")

    @pytest.mark.asyncio
    async def test_cancel_debate_wrong_user(self, service):
        """Should deny cancelling other user's debate."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        debate = await service.create_debate("user-123", request)

        with pytest.raises(DebateAccessDeniedError):
            await service.cancel_debate(debate.id, "other-user")

    @pytest.mark.asyncio
    async def test_delete_debate(self, service):
        """Should delete a debate."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        debate = await service.create_debate("user-123", request)
        result = await service.delete_debate(debate.id, "user-123")

        assert result is True
        assert await service.get_debate(debate.id, "user-123") is None

    @pytest.mark.asyncio
    async def test_delete_debate_not_found(self, service):
        """Should raise error for non-existent debate."""
        with pytest.raises(DebateNotFoundError):
            await service.delete_debate("non-existent", "user-123")

    @pytest.mark.asyncio
    async def test_delete_debate_wrong_user(self, service):
        """Should deny deleting other user's debate."""
        request = CreateDebateRequest(
            question="Test",
            provider="anthropic",
            model="claude",
        )
        debate = await service.create_debate("user-123", request)

        with pytest.raises(DebateAccessDeniedError):
            await service.delete_debate(debate.id, "other-user")


class TestGetDebateService:
    def test_get_debate_service_returns_singleton(self):
        """Should return the same instance."""
        # Reset the singleton
        import modules.debates.service as service_module
        service_module._service_instance = None

        service1 = get_debate_service()
        service2 = get_debate_service()

        assert service1 is service2

        # Cleanup
        service_module._service_instance = None

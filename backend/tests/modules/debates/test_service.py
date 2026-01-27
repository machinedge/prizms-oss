"""Tests for debates service with repository layer."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from decimal import Decimal

from modules.debates.service import DebateService, get_debate_service, reset_debate_service
from modules.debates.repository import DebateRepository, reset_debate_repository
from modules.debates.models import (
    CreateDebateRequest,
    Debate,
    DebateListResponse,
    DebateListItem,
    DebateStatus,
    DebateSettings,
    DebateEventType,
)
from modules.debates.exceptions import DebateNotFoundError, DebateAccessDeniedError


def create_mock_debate(
    debate_id: str = "debate-123",
    user_id: str = "user-123",
    question: str = "Test question",
    status: DebateStatus = DebateStatus.PENDING,
) -> Debate:
    """Helper to create a mock Debate model."""
    now = datetime.now(timezone.utc)
    return Debate(
        id=debate_id,
        user_id=user_id,
        question=question,
        status=status,
        provider="anthropic",
        model="claude-3-5-sonnet",
        max_rounds=3,
        current_round=0,
        settings=DebateSettings(
            max_rounds=3,
            temperature=0.7,
            personalities=["optimist", "pessimist", "analyst"],
            include_synthesis=True,
        ),
        rounds=[],
        synthesis=None,
        total_input_tokens=0,
        total_output_tokens=0,
        total_cost=Decimal("0"),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before each test."""
    reset_debate_service()
    reset_debate_repository()
    yield
    reset_debate_service()
    reset_debate_repository()


class TestDebateService:
    @pytest.mark.asyncio
    async def test_create_debate(self):
        """Should create a debate via repository."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        expected_debate = create_mock_debate()
        mock_repo.create_debate.return_value = expected_debate

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
        mock_repo.create_debate.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_debate_with_custom_settings(self):
        """Should create a debate with custom settings."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        expected_debate = create_mock_debate()
        expected_debate = expected_debate.model_copy(update={
            "max_rounds": 5,
            "settings": DebateSettings(
                max_rounds=5,
                temperature=0.9,
                personalities=["optimist", "pessimist"],
            ),
        })
        mock_repo.create_debate.return_value = expected_debate

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
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        expected_debate = create_mock_debate()
        mock_repo.get_debate_by_id.return_value = expected_debate

        fetched = await service.get_debate("debate-123", "user-123")

        assert fetched is not None
        assert fetched.id == "debate-123"
        assert fetched.question == "Test question"
        mock_repo.get_debate_by_id.assert_called_once_with("debate-123")

    @pytest.mark.asyncio
    async def test_get_debate_not_found(self):
        """Should return None for non-existent debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        mock_repo.get_debate_by_id.return_value = None

        result = await service.get_debate("non-existent-id", "user-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_debate_wrong_user(self):
        """Should deny access to other user's debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        # Debate belongs to user-123, but other-user is requesting
        debate = create_mock_debate(user_id="user-123")
        mock_repo.get_debate_by_id.return_value = debate

        with pytest.raises(DebateAccessDeniedError) as exc_info:
            await service.get_debate("debate-123", "other-user")

        assert exc_info.value.code == "DEBATE_ACCESS_DENIED"
        assert exc_info.value.details["debate_id"] == "debate-123"
        assert exc_info.value.details["user_id"] == "other-user"

    @pytest.mark.asyncio
    async def test_list_debates(self):
        """Should list user's debates via repository."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        now = datetime.now(timezone.utc)
        expected_response = DebateListResponse(
            debates=[
                DebateListItem(
                    id="debate-1",
                    question="Test 1",
                    status=DebateStatus.PENDING,
                    provider="anthropic",
                    model="claude",
                    current_round=0,
                    max_rounds=3,
                    total_cost=Decimal("0"),
                    created_at=now,
                ),
                DebateListItem(
                    id="debate-2",
                    question="Test 2",
                    status=DebateStatus.PENDING,
                    provider="anthropic",
                    model="claude",
                    current_round=0,
                    max_rounds=3,
                    total_cost=Decimal("0"),
                    created_at=now,
                ),
            ],
            total=2,
            page=1,
            page_size=20,
            has_more=False,
        )
        mock_repo.list_debates.return_value = expected_response

        response = await service.list_debates("user-123")

        assert response.total == 2
        assert len(response.debates) == 2
        assert response.page == 1
        assert response.has_more is False
        mock_repo.list_debates.assert_called_once_with("user-123", 1, 20, None)

    @pytest.mark.asyncio
    async def test_list_debates_pagination(self):
        """Should paginate debate list."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        now = datetime.now(timezone.utc)
        expected_response = DebateListResponse(
            debates=[
                DebateListItem(
                    id="debate-1",
                    question="Test 1",
                    status=DebateStatus.PENDING,
                    provider="anthropic",
                    model="claude",
                    current_round=0,
                    max_rounds=3,
                    total_cost=Decimal("0"),
                    created_at=now,
                ),
            ],
            total=3,
            page=1,
            page_size=2,
            has_more=True,
        )
        mock_repo.list_debates.return_value = expected_response

        response = await service.list_debates("user-123", page=1, page_size=2)

        assert response.total == 3
        assert len(response.debates) == 1
        assert response.has_more is True
        mock_repo.list_debates.assert_called_once_with("user-123", 1, 2, None)

    @pytest.mark.asyncio
    async def test_list_debates_filter_by_status(self):
        """Should filter debates by status."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        now = datetime.now(timezone.utc)
        expected_response = DebateListResponse(
            debates=[
                DebateListItem(
                    id="debate-1",
                    question="Test 1",
                    status=DebateStatus.PENDING,
                    provider="anthropic",
                    model="claude",
                    current_round=0,
                    max_rounds=3,
                    total_cost=Decimal("0"),
                    created_at=now,
                ),
            ],
            total=1,
            page=1,
            page_size=20,
            has_more=False,
        )
        mock_repo.list_debates.return_value = expected_response

        response = await service.list_debates("user-123", status=DebateStatus.PENDING)

        assert response.total == 1
        mock_repo.list_debates.assert_called_once_with("user-123", 1, 20, DebateStatus.PENDING)

    @pytest.mark.asyncio
    async def test_start_debate_stream_not_found(self):
        """Should yield error event for non-existent debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        mock_repo.get_debate_by_id.return_value = None

        events = []
        async for event in service.start_debate_stream("non-existent", "user-123"):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == DebateEventType.ERROR
        assert "not found" in events[0].error.lower()

    @pytest.mark.asyncio
    async def test_start_debate_stream_already_completed(self):
        """Should yield error event for non-pending debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        debate = create_mock_debate(status=DebateStatus.COMPLETED)
        mock_repo.get_debate_by_id.return_value = debate

        events = []
        async for event in service.start_debate_stream("debate-123", "user-123"):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == DebateEventType.ERROR
        assert "already completed" in events[0].error.lower()

    @pytest.mark.asyncio
    async def test_cancel_debate(self):
        """Should cancel a debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        original_debate = create_mock_debate()
        cancelled_debate = original_debate.model_copy(update={"status": DebateStatus.CANCELLED})

        # First call returns original, second returns cancelled
        mock_repo.get_debate_by_id.side_effect = [original_debate, cancelled_debate]

        cancelled = await service.cancel_debate("debate-123", "user-123")

        assert cancelled.status == DebateStatus.CANCELLED
        mock_repo.update_status.assert_called_once_with(
            "debate-123", DebateStatus.CANCELLED, None, None
        )

    @pytest.mark.asyncio
    async def test_cancel_debate_not_found(self):
        """Should raise error for non-existent debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        mock_repo.get_debate_by_id.return_value = None

        with pytest.raises(DebateNotFoundError):
            await service.cancel_debate("non-existent", "user-123")

    @pytest.mark.asyncio
    async def test_cancel_debate_wrong_user(self):
        """Should deny cancelling other user's debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        debate = create_mock_debate(user_id="user-123")
        mock_repo.get_debate_by_id.return_value = debate

        with pytest.raises(DebateAccessDeniedError):
            await service.cancel_debate("debate-123", "other-user")

    @pytest.mark.asyncio
    async def test_delete_debate(self):
        """Should delete a debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        debate = create_mock_debate()
        mock_repo.get_debate_by_id.return_value = debate
        mock_repo.delete.return_value = True

        result = await service.delete_debate("debate-123", "user-123")

        assert result is True
        mock_repo.delete.assert_called_once_with("debate-123")

    @pytest.mark.asyncio
    async def test_delete_debate_not_found(self):
        """Should raise error for non-existent debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        mock_repo.get_debate_by_id.return_value = None

        with pytest.raises(DebateNotFoundError):
            await service.delete_debate("non-existent", "user-123")

    @pytest.mark.asyncio
    async def test_delete_debate_wrong_user(self):
        """Should deny deleting other user's debate."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        debate = create_mock_debate(user_id="user-123")
        mock_repo.get_debate_by_id.return_value = debate

        with pytest.raises(DebateAccessDeniedError):
            await service.delete_debate("debate-123", "other-user")

    @pytest.mark.asyncio
    async def test_update_debate_status(self):
        """Should update debate status via repository."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        await service.update_debate_status("debate-123", DebateStatus.ACTIVE)

        mock_repo.update_status.assert_called_once_with(
            "debate-123", DebateStatus.ACTIVE, None, None
        )

    @pytest.mark.asyncio
    async def test_update_debate_totals(self):
        """Should update debate totals via repository."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        await service.update_debate_totals("debate-123", 1000, 500, Decimal("0.05"))

        mock_repo.update_totals.assert_called_once_with(
            "debate-123", 1000, 500, Decimal("0.05")
        )

    @pytest.mark.asyncio
    async def test_save_round(self):
        """Should save round via repository."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        mock_repo.save_round.return_value = "round-123"

        round_id = await service.save_round("debate-123", 1)

        assert round_id == "round-123"
        mock_repo.save_round.assert_called_once_with("debate-123", 1)

    @pytest.mark.asyncio
    async def test_save_synthesis(self):
        """Should save synthesis via repository."""
        mock_repo = MagicMock(spec=DebateRepository)
        service = DebateService(repository=mock_repo)

        mock_repo.save_synthesis.return_value = "synthesis-123"

        synthesis_id = await service.save_synthesis(
            "debate-123", "Final synthesis", 500, 200, Decimal("0.005")
        )

        assert synthesis_id == "synthesis-123"
        mock_repo.save_synthesis.assert_called_once_with(
            "debate-123", "Final synthesis", 500, 200, Decimal("0.005")
        )


class TestGetDebateService:
    def test_get_debate_service_returns_singleton(self):
        """Should return the same instance."""
        with patch("modules.debates.repository.get_debate_repository") as mock_get_repo:
            mock_get_repo.return_value = MagicMock(spec=DebateRepository)

            service1 = get_debate_service()
            service2 = get_debate_service()

            assert service1 is service2

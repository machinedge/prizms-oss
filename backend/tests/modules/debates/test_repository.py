"""Tests for debates repository."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from modules.debates.repository import (
    DebateRepository,
    get_debate_repository,
    reset_debate_repository,
)
from modules.debates.models import (
    DebateStatus,
    PersonalityResponse,
)


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


def create_mock_round_data(
    round_id: str = "round-123",
    debate_id: str = "debate-123",
    round_number: int = 1,
    responses: list = None,
) -> dict:
    """Helper to create mock round data."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": round_id,
        "debate_id": debate_id,
        "round_number": round_number,
        "created_at": now,
        "debate_responses": responses or [],
    }


def create_mock_response_data(
    response_id: str = "response-123",
    personality_name: str = "analyst",
) -> dict:
    """Helper to create mock response data."""
    return {
        "id": response_id,
        "personality_name": personality_name,
        "thinking_content": "Some thinking...",
        "answer_content": "Some answer...",
        "input_tokens": 100,
        "output_tokens": 50,
        "cost": "0.001",
    }


def create_mock_synthesis_data(
    synthesis_id: str = "synthesis-123",
    debate_id: str = "debate-123",
) -> dict:
    """Helper to create mock synthesis data."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": synthesis_id,
        "debate_id": debate_id,
        "content": "Final synthesis content",
        "input_tokens": 500,
        "output_tokens": 200,
        "cost": "0.005",
        "created_at": now,
    }


@pytest.fixture(autouse=True)
def reset_repository_singleton():
    """Reset the repository singleton before each test."""
    reset_debate_repository()
    yield
    reset_debate_repository()


class TestDebateRepositoryCreateDebate:
    """Tests for create_debate method."""

    def test_create_debate(self):
        """Should create a debate and return mapped model."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            create_mock_debate_data()
        ]

        data = {
            "user_id": "user-123",
            "question": "Test question",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "max_rounds": 3,
            "settings": {"max_rounds": 3, "temperature": 0.7},
            "status": "pending",
            "current_round": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0,
        }

        debate = repo.create_debate(data)

        assert debate.id == "debate-123"
        assert debate.user_id == "user-123"
        assert debate.status == DebateStatus.PENDING
        assert debate.provider == "anthropic"
        mock_db.table.assert_called_with("debates")


class TestDebateRepositoryGetDebate:
    """Tests for get_debate_by_id method."""

    def test_get_debate_by_id(self):
        """Should get a debate by ID with all related data."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        debate_data = create_mock_debate_data()
        round_data = create_mock_round_data(responses=[
            create_mock_response_data()
        ])
        synthesis_data = create_mock_synthesis_data()

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

        mock_db.table.side_effect = table_router

        debates_table.select.return_value.eq.return_value.execute.return_value.data = [debate_data]
        rounds_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [round_data]
        synthesis_table.select.return_value.eq.return_value.execute.return_value.data = [synthesis_data]

        debate = repo.get_debate_by_id("debate-123")

        assert debate is not None
        assert debate.id == "debate-123"
        assert len(debate.rounds) == 1
        assert len(debate.rounds[0].responses) == 1
        assert debate.synthesis is not None
        assert debate.synthesis.content == "Final synthesis content"

    def test_get_debate_by_id_not_found(self):
        """Should return None for non-existent debate."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        result = repo.get_debate_by_id("non-existent")
        assert result is None

    def test_get_debate_by_id_without_rounds(self):
        """Should get debate without loading rounds."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        debate_data = create_mock_debate_data()

        # Only debates table should be queried
        debates_table = MagicMock()
        synthesis_table = MagicMock()

        def table_router(name):
            if name == "debates":
                return debates_table
            elif name == "debate_synthesis":
                return synthesis_table
            return MagicMock()

        mock_db.table.side_effect = table_router

        debates_table.select.return_value.eq.return_value.execute.return_value.data = [debate_data]
        synthesis_table.select.return_value.eq.return_value.execute.return_value.data = []

        debate = repo.get_debate_by_id("debate-123", include_rounds=False)

        assert debate is not None
        assert debate.id == "debate-123"
        assert len(debate.rounds) == 0


class TestDebateRepositoryListDebates:
    """Tests for list_debates method."""

    def test_list_debates(self):
        """Should list debates with pagination."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        now = datetime.now(timezone.utc).isoformat()

        count_result = MagicMock()
        count_result.count = 2

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

        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = count_result
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = data_result

        response = repo.list_debates("user-123")

        assert response.total == 2
        assert len(response.debates) == 2
        assert response.page == 1
        assert response.page_size == 20
        assert response.has_more is False

    def test_list_debates_with_status_filter(self):
        """Should filter debates by status."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        now = datetime.now(timezone.utc).isoformat()

        count_result = MagicMock()
        count_result.count = 1

        data_result = MagicMock()
        data_result.data = [
            {
                "id": "debate-1",
                "question": "Test 1",
                "status": "completed",
                "provider": "anthropic",
                "model": "claude",
                "max_rounds": 3,
                "current_round": 3,
                "total_cost": "0.1",
                "created_at": now,
            },
        ]

        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = count_result
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = data_result

        response = repo.list_debates("user-123", status=DebateStatus.COMPLETED)

        assert response.total == 1
        assert response.debates[0].status == DebateStatus.COMPLETED

    def test_list_debates_truncates_long_questions(self):
        """Should truncate long questions to 100 chars + ellipsis."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

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

        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = count_result
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = data_result

        response = repo.list_debates("user-123")

        assert len(response.debates[0].question) == 103  # 100 + "..."
        assert response.debates[0].question.endswith("...")


class TestDebateRepositoryUpdateStatus:
    """Tests for update_status method."""

    def test_update_status(self):
        """Should update debate status."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        repo.update_status("debate-123", DebateStatus.ACTIVE)

        mock_db.table.assert_called_with("debates")
        update_call = mock_db.table.return_value.update
        update_call.assert_called_once()
        update_data = update_call.call_args[0][0]
        assert update_data["status"] == "active"
        assert "started_at" in update_data

    def test_update_status_completed(self):
        """Should set completed_at when status is COMPLETED."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        repo.update_status("debate-123", DebateStatus.COMPLETED)

        update_call = mock_db.table.return_value.update
        update_data = update_call.call_args[0][0]
        assert update_data["status"] == "completed"
        assert "completed_at" in update_data

    def test_update_status_with_round(self):
        """Should update current round."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        repo.update_status("debate-123", DebateStatus.ACTIVE, current_round=2)

        update_call = mock_db.table.return_value.update
        update_data = update_call.call_args[0][0]
        assert update_data["current_round"] == 2

    def test_update_status_with_error(self):
        """Should set error message."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        repo.update_status("debate-123", DebateStatus.FAILED, error_message="Something went wrong")

        update_call = mock_db.table.return_value.update
        update_data = update_call.call_args[0][0]
        assert update_data["error_message"] == "Something went wrong"


class TestDebateRepositoryUpdateTotals:
    """Tests for update_totals method."""

    def test_update_totals(self):
        """Should update token and cost totals."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        repo.update_totals("debate-123", 1000, 500, Decimal("0.05"))

        mock_db.table.assert_called_with("debates")
        update_call = mock_db.table.return_value.update
        update_data = update_call.call_args[0][0]
        assert update_data["total_input_tokens"] == 1000
        assert update_data["total_output_tokens"] == 500
        assert update_data["total_cost"] == 0.05


class TestDebateRepositoryDelete:
    """Tests for delete method."""

    def test_delete(self):
        """Should delete debate."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        result = repo.delete("debate-123")

        assert result is True
        mock_db.table.assert_called_with("debates")
        mock_db.table.return_value.delete.assert_called_once()


class TestDebateRepositorySaveRound:
    """Tests for save_round method."""

    def test_save_round(self):
        """Should save a round and return ID."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "round-123"}
        ]

        round_id = repo.save_round("debate-123", 1)

        assert round_id == "round-123"
        mock_db.table.assert_called_with("debate_rounds")
        insert_call = mock_db.table.return_value.insert
        insert_data = insert_call.call_args[0][0]
        assert insert_data["debate_id"] == "debate-123"
        assert insert_data["round_number"] == 1


class TestDebateRepositorySaveResponse:
    """Tests for save_response method."""

    def test_save_response(self):
        """Should save a response and return ID."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "response-123"}
        ]

        response = PersonalityResponse(
            personality_name="analyst",
            thinking_content="Some thinking",
            answer_content="Some answer",
            input_tokens=100,
            output_tokens=50,
            cost=Decimal("0.001"),
        )

        response_id = repo.save_response("round-123", response)

        assert response_id == "response-123"
        mock_db.table.assert_called_with("debate_responses")
        insert_call = mock_db.table.return_value.insert
        insert_data = insert_call.call_args[0][0]
        assert insert_data["round_id"] == "round-123"
        assert insert_data["personality_name"] == "analyst"
        assert insert_data["cost"] == 0.001


class TestDebateRepositorySaveSynthesis:
    """Tests for save_synthesis method."""

    def test_save_synthesis(self):
        """Should save synthesis and return ID."""
        mock_db = MagicMock()
        repo = DebateRepository(mock_db)

        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "synthesis-123"}
        ]

        synthesis_id = repo.save_synthesis(
            debate_id="debate-123",
            content="Final synthesis",
            input_tokens=500,
            output_tokens=200,
            cost=Decimal("0.005"),
        )

        assert synthesis_id == "synthesis-123"
        mock_db.table.assert_called_with("debate_synthesis")
        insert_call = mock_db.table.return_value.insert
        insert_data = insert_call.call_args[0][0]
        assert insert_data["debate_id"] == "debate-123"
        assert insert_data["content"] == "Final synthesis"
        assert insert_data["cost"] == 0.005


class TestGetDebateRepository:
    """Tests for get_debate_repository singleton."""

    def test_get_debate_repository_returns_singleton(self):
        """Should return the same instance."""
        from unittest.mock import patch

        with patch("shared.database.get_supabase_client") as mock_get_client:
            mock_get_client.return_value = MagicMock()

            repo1 = get_debate_repository()
            repo2 = get_debate_repository()

            assert repo1 is repo2

    def test_reset_debate_repository(self):
        """Should reset the singleton."""
        from unittest.mock import patch

        with patch("shared.database.get_supabase_client") as mock_get_client:
            mock_get_client.side_effect = [MagicMock(), MagicMock()]

            repo1 = get_debate_repository()
            reset_debate_repository()
            repo2 = get_debate_repository()

            assert repo1 is not repo2

"""
Debate repository for database access.

Encapsulates all Supabase queries and data mapping for debate-related tables:
- debates
- debate_rounds
- debate_responses
- debate_synthesis
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any

from supabase import Client

from shared.repository import BaseRepository
from .models import (
    Debate,
    DebateListItem,
    DebateListResponse,
    DebateRound,
    DebateSettings,
    DebateStatus,
    DebateSynthesis,
    PersonalityResponse,
)


class DebateRepository(BaseRepository[Debate]):
    """
    Repository for debate data access.

    Handles all database operations for debates and related entities.
    All methods return Pydantic models with proper mapping from database rows.

    Note: This repository does NOT perform authorization checks.
    The service layer is responsible for verifying user ownership.
    """

    # -------------------------------------------------------------------------
    # Debate CRUD operations
    # -------------------------------------------------------------------------

    def create_debate(self, data: dict[str, Any]) -> Debate:
        """
        Create a new debate record.

        Args:
            data: Dictionary with debate fields (user_id, question, provider, etc.)

        Returns:
            Created Debate with generated ID and timestamps.
        """
        result = self._db.table("debates").insert(data).execute()
        debate_data = result.data[0]
        return self._map_to_debate(debate_data)

    def get_debate_by_id(
        self,
        debate_id: str,
        include_rounds: bool = True,
        include_synthesis: bool = True,
    ) -> Optional[Debate]:
        """
        Get a debate by ID with optional related data.

        Args:
            debate_id: The debate UUID.
            include_rounds: Whether to load rounds and responses.
            include_synthesis: Whether to load synthesis.

        Returns:
            Debate with all requested data, or None if not found.
        """
        result = self._db.table("debates").select("*").eq("id", debate_id).execute()

        if not result.data:
            return None

        debate_data = result.data[0]

        rounds: list[DebateRound] = []
        synthesis: Optional[DebateSynthesis] = None

        if include_rounds:
            rounds = self._get_rounds_for_debate(debate_id)

        if include_synthesis:
            synthesis = self._get_synthesis_for_debate(debate_id)

        return self._map_to_debate(debate_data, rounds, synthesis)

    def list_debates(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[DebateStatus] = None,
    ) -> DebateListResponse:
        """
        List debates for a user with pagination.

        Args:
            user_id: The user's ID.
            page: Page number (1-indexed).
            page_size: Items per page.
            status: Optional status filter.

        Returns:
            Paginated list response with debate items.
        """
        offset = (page - 1) * page_size

        # Build base query for counting
        count_query = self._db.table("debates").select("*", count="exact").eq("user_id", user_id)
        if status:
            count_query = count_query.eq("status", status.value)

        # Get total count
        count_result = count_query.execute()
        total = count_result.count or 0

        # Build query for paginated results
        query = self._db.table("debates").select("*").eq("user_id", user_id)
        if status:
            query = query.eq("status", status.value)

        result = query.order("created_at", desc=True).range(offset, offset + page_size - 1).execute()

        debates = [self._map_to_list_item(d) for d in result.data]

        return DebateListResponse(
            debates=debates,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    def update_status(
        self,
        debate_id: str,
        status: DebateStatus,
        current_round: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Update debate status and optionally current round or error message.

        Args:
            debate_id: The debate UUID.
            status: New status.
            current_round: Optional round number update.
            error_message: Optional error message for failed debates.
        """
        data: dict[str, Any] = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if current_round is not None:
            data["current_round"] = current_round

        if error_message is not None:
            data["error_message"] = error_message

        if status == DebateStatus.COMPLETED:
            data["completed_at"] = datetime.now(timezone.utc).isoformat()
        elif status == DebateStatus.ACTIVE:
            data["started_at"] = datetime.now(timezone.utc).isoformat()

        self._db.table("debates").update(data).eq("id", debate_id).execute()

    def update_totals(
        self,
        debate_id: str,
        total_input_tokens: int,
        total_output_tokens: int,
        total_cost: Decimal,
    ) -> None:
        """
        Update debate token and cost totals.

        Args:
            debate_id: The debate UUID.
            total_input_tokens: Total input tokens used.
            total_output_tokens: Total output tokens used.
            total_cost: Total cost as Decimal.
        """
        data = {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cost": float(total_cost),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._db.table("debates").update(data).eq("id", debate_id).execute()

    def delete(self, debate_id: str) -> bool:
        """
        Delete a debate and all associated data.

        Args:
            debate_id: The debate UUID.

        Returns:
            True if deletion was executed.

        Note: Related records are deleted via CASCADE.
        """
        self._db.table("debates").delete().eq("id", debate_id).execute()
        return True

    # -------------------------------------------------------------------------
    # Round operations
    # -------------------------------------------------------------------------

    def save_round(self, debate_id: str, round_number: int) -> str:
        """
        Create a new round record.

        Args:
            debate_id: The parent debate UUID.
            round_number: The round number (1-indexed).

        Returns:
            The ID of the created round.
        """
        data = {
            "debate_id": debate_id,
            "round_number": round_number,
        }
        result = self._db.table("debate_rounds").insert(data).execute()
        return str(result.data[0]["id"])

    # -------------------------------------------------------------------------
    # Response operations
    # -------------------------------------------------------------------------

    def save_response(self, round_id: str, response: PersonalityResponse) -> str:
        """
        Save a personality response.

        Args:
            round_id: The parent round UUID.
            response: The PersonalityResponse to save.

        Returns:
            The ID of the created response.
        """
        data = {
            "round_id": round_id,
            "personality_name": response.personality_name,
            "thinking_content": response.thinking_content,
            "answer_content": response.answer_content,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost": float(response.cost),
        }
        result = self._db.table("debate_responses").insert(data).execute()
        return str(result.data[0]["id"])

    # -------------------------------------------------------------------------
    # Synthesis operations
    # -------------------------------------------------------------------------

    def save_synthesis(
        self,
        debate_id: str,
        content: str,
        input_tokens: int,
        output_tokens: int,
        cost: Decimal,
    ) -> str:
        """
        Save the debate synthesis.

        Args:
            debate_id: The parent debate UUID.
            content: The synthesis text.
            input_tokens: Input tokens used.
            output_tokens: Output tokens used.
            cost: Cost as Decimal.

        Returns:
            The ID of the created synthesis.
        """
        data = {
            "debate_id": debate_id,
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": float(cost),
        }
        result = self._db.table("debate_synthesis").insert(data).execute()
        return str(result.data[0]["id"])

    # -------------------------------------------------------------------------
    # Private helper methods for data loading
    # -------------------------------------------------------------------------

    def _get_rounds_for_debate(self, debate_id: str) -> list[DebateRound]:
        """Load all rounds with nested responses for a debate."""
        rounds_result = self._db.table("debate_rounds").select(
            "*, debate_responses(*)"
        ).eq("debate_id", debate_id).order("round_number").execute()

        rounds = []
        for round_data in rounds_result.data:
            rounds.append(self._map_to_round(round_data, debate_id))

        return rounds

    def _get_synthesis_for_debate(self, debate_id: str) -> Optional[DebateSynthesis]:
        """Load synthesis for a debate if it exists."""
        synth_result = self._db.table("debate_synthesis").select("*").eq("debate_id", debate_id).execute()
        if synth_result.data:
            return self._map_to_synthesis(synth_result.data[0], debate_id)
        return None

    # -------------------------------------------------------------------------
    # Private mapping methods
    # -------------------------------------------------------------------------

    def _map_to_debate(
        self,
        data: dict[str, Any],
        rounds: Optional[list[DebateRound]] = None,
        synthesis: Optional[DebateSynthesis] = None,
    ) -> Debate:
        """Map database row to Debate model."""
        settings_data = data.get("settings", {})
        settings = DebateSettings(**settings_data) if settings_data else DebateSettings()

        return Debate(
            id=str(data["id"]),
            user_id=str(data["user_id"]),
            question=data["question"],
            status=DebateStatus(data["status"]),
            provider=data["provider"],
            model=data["model"],
            settings=settings,
            max_rounds=data["max_rounds"],
            current_round=data["current_round"],
            rounds=rounds or [],
            synthesis=synthesis,
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            total_cost=Decimal(str(data.get("total_cost", 0))),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            error_message=data.get("error_message"),
        )

    def _map_to_round(self, round_data: dict[str, Any], debate_id: str) -> DebateRound:
        """Map database row to DebateRound model with nested responses."""
        responses = [
            PersonalityResponse(
                personality_name=r["personality_name"],
                thinking_content=r.get("thinking_content"),
                answer_content=r.get("answer_content", ""),
                input_tokens=r.get("input_tokens", 0),
                output_tokens=r.get("output_tokens", 0),
                cost=Decimal(str(r.get("cost", 0))),
            )
            for r in round_data.get("debate_responses", [])
        ]

        return DebateRound(
            id=str(round_data["id"]),
            debate_id=debate_id,
            round_number=round_data["round_number"],
            responses=responses,
            created_at=round_data["created_at"],
        )

    def _map_to_synthesis(self, synth_data: dict[str, Any], debate_id: str) -> DebateSynthesis:
        """Map database row to DebateSynthesis model."""
        return DebateSynthesis(
            id=str(synth_data["id"]),
            debate_id=debate_id,
            content=synth_data["content"],
            input_tokens=synth_data.get("input_tokens", 0),
            output_tokens=synth_data.get("output_tokens", 0),
            cost=Decimal(str(synth_data.get("cost", 0))),
            created_at=synth_data["created_at"],
        )

    def _map_to_list_item(self, data: dict[str, Any]) -> DebateListItem:
        """Map database row to DebateListItem model."""
        question = data["question"]
        truncated_question = question[:100] + "..." if len(question) > 100 else question

        return DebateListItem(
            id=str(data["id"]),
            question=truncated_question,
            status=DebateStatus(data["status"]),
            provider=data["provider"],
            model=data["model"],
            current_round=data["current_round"],
            max_rounds=data["max_rounds"],
            total_cost=Decimal(str(data.get("total_cost", 0))),
            created_at=data["created_at"],
        )



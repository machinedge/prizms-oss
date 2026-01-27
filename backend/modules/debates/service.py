"""
Debates service implementation with Supabase.

Provides CRUD operations for debates with real database persistence.
Streaming functionality will be completed in Story 14.
"""

from typing import Optional, AsyncIterator, Any
from datetime import datetime, timezone
from decimal import Decimal

from supabase import Client

from .interfaces import IDebateService
from .models import (
    Debate,
    DebateListItem,
    DebateListResponse,
    CreateDebateRequest,
    DebateEvent,
    DebateEventType,
    DebateStatus,
    DebateRound,
    DebateSettings,
    PersonalityResponse,
    DebateSynthesis,
)
from .exceptions import DebateNotFoundError, DebateAccessDeniedError


class DebateService(IDebateService):
    """
    Debate service with Supabase backend.

    Implements IDebateService protocol with real database operations.
    """

    def __init__(
        self,
        supabase_client: Client,
        auth: Any = None,     # IAuthService - injected
        usage: Any = None,    # IUsageService - injected
    ):
        self._db = supabase_client
        self._auth = auth
        self._usage = usage

    async def create_debate(
        self,
        user_id: str,
        request: CreateDebateRequest,
    ) -> Debate:
        """Create a new debate in the database."""
        data = {
            "user_id": user_id,
            "question": request.question,
            "provider": request.provider,
            "model": request.model,
            "max_rounds": request.settings.max_rounds,
            "settings": request.settings.model_dump(),
            "status": DebateStatus.PENDING.value,
            "current_round": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0,
        }

        result = self._db.table("debates").insert(data).execute()
        debate_data = result.data[0]

        return self._map_to_debate(debate_data)

    async def get_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> Optional[Debate]:
        """Get a debate by ID with all rounds and responses."""
        # Get debate - using service role, so we need to check user_id manually
        result = self._db.table("debates").select("*").eq("id", debate_id).execute()

        if not result.data:
            return None

        debate_data = result.data[0]

        # Check ownership
        if debate_data["user_id"] != user_id:
            raise DebateAccessDeniedError(debate_id, user_id)

        # Get rounds with responses
        rounds_result = self._db.table("debate_rounds").select(
            "*, debate_responses(*)"
        ).eq("debate_id", debate_id).order("round_number").execute()

        rounds = []
        for round_data in rounds_result.data:
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
            rounds.append(DebateRound(
                id=str(round_data["id"]),
                debate_id=debate_id,
                round_number=round_data["round_number"],
                responses=responses,
                created_at=round_data["created_at"],
            ))

        # Get synthesis if exists
        synthesis = None
        synth_result = self._db.table("debate_synthesis").select("*").eq("debate_id", debate_id).execute()
        if synth_result.data:
            synth_data = synth_result.data[0]
            synthesis = DebateSynthesis(
                id=str(synth_data["id"]),
                debate_id=debate_id,
                content=synth_data["content"],
                input_tokens=synth_data.get("input_tokens", 0),
                output_tokens=synth_data.get("output_tokens", 0),
                cost=Decimal(str(synth_data.get("cost", 0))),
                created_at=synth_data["created_at"],
            )

        return self._map_to_debate(debate_data, rounds, synthesis)

    async def list_debates(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[DebateStatus] = None,
    ) -> DebateListResponse:
        """List debates for a user with pagination."""
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

        debates = [
            DebateListItem(
                id=str(d["id"]),
                question=d["question"][:100] + "..." if len(d["question"]) > 100 else d["question"],
                status=DebateStatus(d["status"]),
                provider=d["provider"],
                model=d["model"],
                current_round=d["current_round"],
                max_rounds=d["max_rounds"],
                total_cost=Decimal(str(d.get("total_cost", 0))),
                created_at=d["created_at"],
            )
            for d in result.data
        ]

        return DebateListResponse(
            debates=debates,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def start_debate_stream(
        self,
        debate_id: str,
        user_id: str,
    ) -> AsyncIterator[DebateEvent]:
        """Start debate and stream events."""
        debate = await self.get_debate(debate_id, user_id)

        if debate is None:
            raise DebateNotFoundError(debate_id)

        # Update status to active
        await self.update_debate_status(debate_id, DebateStatus.ACTIVE)

        # Yield started event
        yield DebateEvent(
            type=DebateEventType.DEBATE_STARTED,
            debate_id=debate_id,
        )

        # TODO: Implement actual debate execution in Story 14
        # For now, just yield a completed event
        await self.update_debate_status(debate_id, DebateStatus.COMPLETED)

        yield DebateEvent(
            type=DebateEventType.DEBATE_COMPLETED,
            debate_id=debate_id,
        )

    async def cancel_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> Debate:
        """Cancel an active or pending debate."""
        debate = await self.get_debate(debate_id, user_id)

        if debate is None:
            raise DebateNotFoundError(debate_id)

        # Update status in database
        await self.update_debate_status(debate_id, DebateStatus.CANCELLED)

        # Return updated debate
        return await self.get_debate(debate_id, user_id)  # type: ignore

    async def delete_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> bool:
        """Delete a debate and all associated data."""
        debate = await self.get_debate(debate_id, user_id)

        if debate is None:
            raise DebateNotFoundError(debate_id)

        # Delete from database (CASCADE handles related records)
        self._db.table("debates").delete().eq("id", debate_id).execute()
        return True

    async def update_debate_status(
        self,
        debate_id: str,
        status: DebateStatus,
        current_round: Optional[int] = None,
    ) -> None:
        """Update debate status and optionally current round."""
        data: dict[str, Any] = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if current_round is not None:
            data["current_round"] = current_round

        if status == DebateStatus.COMPLETED:
            data["completed_at"] = datetime.now(timezone.utc).isoformat()
        elif status == DebateStatus.ACTIVE:
            data["started_at"] = datetime.now(timezone.utc).isoformat()

        self._db.table("debates").update(data).eq("id", debate_id).execute()

    def _map_to_debate(
        self,
        data: dict,
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


# Module-level instance getter
_service_instance: Optional[DebateService] = None


def get_debate_service() -> DebateService:
    """Get the debate service singleton."""
    global _service_instance
    if _service_instance is None:
        from shared.database import get_supabase_client
        _service_instance = DebateService(
            supabase_client=get_supabase_client(),
        )
    return _service_instance


def reset_debate_service() -> None:
    """Reset the debate service singleton (for testing)."""
    global _service_instance
    _service_instance = None

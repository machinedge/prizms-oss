"""
Debate service for business logic.
"""

from typing import Optional
from datetime import datetime, timezone

from ..models.debate import (
    CreateDebateRequest,
    DebateResponse,
    DebateListItem,
    DebateListResponse,
    DebateRound,
    PersonalityResponse,
    DebateSynthesis,
    DebateStatus,
)
from .database import get_supabase_client


class DebateService:
    """Service for debate operations."""

    def __init__(self):
        self.db = get_supabase_client()

    async def create_debate(
        self,
        user_id: str,
        request: CreateDebateRequest,
    ) -> DebateResponse:
        """Create a new debate."""
        data = {
            "user_id": user_id,
            "question": request.question,
            "provider": request.provider,
            "model": request.model,
            "max_rounds": request.settings.max_rounds,
            "settings": request.settings.model_dump(),
            "status": DebateStatus.PENDING.value,
        }

        result = self.db.table("debates").insert(data).execute()
        debate_data = result.data[0]

        return self._map_to_response(debate_data)

    async def get_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> Optional[DebateResponse]:
        """Get a debate by ID with all rounds and responses."""
        # Get debate
        result = self.db.table("debates").select("*").eq("id", debate_id).eq("user_id", user_id).execute()

        if not result.data:
            return None

        debate_data = result.data[0]

        # Get rounds with responses
        rounds_result = self.db.table("debate_rounds").select(
            "*, debate_responses(*)"
        ).eq("debate_id", debate_id).order("round_number").execute()

        rounds = []
        for round_data in rounds_result.data:
            responses = [
                PersonalityResponse(
                    personality_name=r["personality_name"],
                    thinking_content=r["thinking_content"],
                    answer_content=r["answer_content"],
                    tokens_used=r["tokens_used"],
                    cost=float(r["cost"]),
                )
                for r in round_data.get("debate_responses", [])
            ]
            rounds.append(DebateRound(
                round_number=round_data["round_number"],
                responses=responses,
                created_at=round_data["created_at"],
            ))

        # Get synthesis if exists
        synthesis = None
        synth_result = self.db.table("debate_synthesis").select("*").eq("debate_id", debate_id).execute()
        if synth_result.data:
            synth_data = synth_result.data[0]
            synthesis = DebateSynthesis(
                content=synth_data["content"],
                tokens_used=synth_data["tokens_used"],
                cost=float(synth_data["cost"]),
                created_at=synth_data["created_at"],
            )

        return self._map_to_response(debate_data, rounds, synthesis)

    async def list_debates(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> DebateListResponse:
        """List debates for a user with pagination."""
        offset = (page - 1) * page_size

        # Get total count
        count_result = self.db.table("debates").select("id", count="exact").eq("user_id", user_id).execute()
        total = count_result.count or 0

        # Get paginated results
        result = self.db.table("debates").select("*").eq("user_id", user_id).order("created_at", desc=True).range(offset, offset + page_size - 1).execute()

        debates = [
            DebateListItem(
                id=str(d["id"]),
                question=d["question"][:100] + "..." if len(d["question"]) > 100 else d["question"],
                status=DebateStatus(d["status"]),
                provider=d["provider"],
                model=d["model"],
                current_round=d["current_round"],
                max_rounds=d["max_rounds"],
                total_cost=float(d["total_cost"]),
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

    async def update_debate_status(
        self,
        debate_id: str,
        status: DebateStatus,
        current_round: Optional[int] = None,
    ) -> None:
        """Update debate status and optionally current round."""
        data = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if current_round is not None:
            data["current_round"] = current_round
        if status == DebateStatus.COMPLETED:
            data["completed_at"] = datetime.now(timezone.utc).isoformat()

        self.db.table("debates").update(data).eq("id", debate_id).execute()

    def _map_to_response(
        self,
        data: dict,
        rounds: list[DebateRound] = None,
        synthesis: DebateSynthesis = None,
    ) -> DebateResponse:
        """Map database row to response model."""
        return DebateResponse(
            id=str(data["id"]),
            question=data["question"],
            status=DebateStatus(data["status"]),
            provider=data["provider"],
            model=data["model"],
            max_rounds=data["max_rounds"],
            current_round=data["current_round"],
            rounds=rounds or [],
            synthesis=synthesis,
            total_tokens=data["total_tokens"],
            total_cost=float(data["total_cost"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            completed_at=data.get("completed_at"),
        )


def get_debate_service() -> DebateService:
    """Get debate service instance."""
    return DebateService()

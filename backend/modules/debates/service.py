"""
Debates service stub implementation.

This is a stub that will be completed in Stories 13-14.
"""

from typing import Optional, AsyncIterator, Any
from datetime import datetime, timezone
import uuid

from .interfaces import IDebateService
from .models import (
    Debate,
    DebateListItem,
    DebateListResponse,
    CreateDebateRequest,
    DebateEvent,
    DebateEventType,
    DebateStatus,
)
from .exceptions import DebateNotFoundError, DebateAccessDeniedError


class DebateService(IDebateService):
    """
    Stub implementation of the debate service.

    Uses in-memory storage for testing. Will be replaced with
    full implementation in Stories 13-14.
    """

    def __init__(
        self,
        auth: Any = None,     # IAuthService - injected
        billing: Any = None,  # IBillingService - injected
        usage: Any = None,    # IUsageService - injected
    ):
        self._auth = auth
        self._billing = billing
        self._usage = usage

        # In-memory storage for testing
        self._debates: dict[str, Debate] = {}

    async def create_debate(
        self,
        user_id: str,
        request: CreateDebateRequest,
    ) -> Debate:
        """Create a new debate."""
        now = datetime.now(timezone.utc)
        debate_id = str(uuid.uuid4())

        debate = Debate(
            id=debate_id,
            user_id=user_id,
            question=request.question,
            status=DebateStatus.PENDING,
            provider=request.provider,
            model=request.model,
            settings=request.settings,
            current_round=0,
            max_rounds=request.settings.max_rounds,
            created_at=now,
            updated_at=now,
        )

        self._debates[debate_id] = debate
        return debate

    async def get_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> Optional[Debate]:
        """Get a debate by ID."""
        debate = self._debates.get(debate_id)

        if debate is None:
            return None

        if debate.user_id != user_id:
            raise DebateAccessDeniedError(debate_id, user_id)

        return debate

    async def list_debates(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[DebateStatus] = None,
    ) -> DebateListResponse:
        """List debates for a user."""
        # Filter by user
        user_debates = [
            d for d in self._debates.values()
            if d.user_id == user_id
        ]

        # Filter by status if specified
        if status:
            user_debates = [d for d in user_debates if d.status == status]

        # Sort by created_at descending
        user_debates.sort(key=lambda d: d.created_at, reverse=True)

        # Paginate
        total = len(user_debates)
        start = (page - 1) * page_size
        end = start + page_size
        page_debates = user_debates[start:end]

        # Convert to list items
        items = [
            DebateListItem(
                id=d.id,
                question=d.question[:100] + "..." if len(d.question) > 100 else d.question,
                status=d.status,
                provider=d.provider,
                model=d.model,
                current_round=d.current_round,
                max_rounds=d.max_rounds,
                total_cost=d.total_cost,
                created_at=d.created_at,
            )
            for d in page_debates
        ]

        return DebateListResponse(
            debates=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
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

        # Yield started event
        yield DebateEvent(
            type=DebateEventType.DEBATE_STARTED,
            debate_id=debate_id,
        )

        # TODO: Implement actual debate execution in Story 14
        # For now, just yield a completed event
        yield DebateEvent(
            type=DebateEventType.DEBATE_COMPLETED,
            debate_id=debate_id,
        )

    async def cancel_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> Debate:
        """Cancel an active debate."""
        debate = await self.get_debate(debate_id, user_id)

        if debate is None:
            raise DebateNotFoundError(debate_id)

        # Create a new Debate with updated status (Pydantic models are immutable by default)
        updated_debate = debate.model_copy(
            update={
                "status": DebateStatus.CANCELLED,
                "updated_at": datetime.now(timezone.utc),
            }
        )

        self._debates[debate_id] = updated_debate
        return updated_debate

    async def delete_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> bool:
        """Delete a debate."""
        debate = await self.get_debate(debate_id, user_id)

        if debate is None:
            raise DebateNotFoundError(debate_id)

        del self._debates[debate_id]
        return True


# Module-level instance getter
_service_instance: Optional[DebateService] = None


def get_debate_service() -> DebateService:
    """Get the debate service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DebateService()
    return _service_instance

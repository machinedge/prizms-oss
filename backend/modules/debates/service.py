"""
Debates service implementation.

Provides business logic for debate operations, delegating data access
to the DebateRepository. Handles authorization checks and orchestration.
"""

from typing import Optional, AsyncIterator, Any
from decimal import Decimal

from .interfaces import IDebateService
from .repository import DebateRepository
from .models import (
    Debate,
    DebateListResponse,
    CreateDebateRequest,
    DebateEvent,
    DebateEventType,
    DebateStatus,
    PersonalityResponse,
)
from .exceptions import DebateNotFoundError, DebateAccessDeniedError


class DebateService(IDebateService):
    """
    Debate service with repository-based data access.

    Implements IDebateService protocol with proper separation of concerns:
    - Authorization checks (user ownership)
    - Business logic (status validation, orchestration)
    - Delegates data access to DebateRepository
    """

    def __init__(
        self,
        repository: DebateRepository,
        auth: Any = None,     # IAuthService - injected
        usage: Any = None,    # IUsageService - injected
    ):
        self._repository = repository
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

        return self._repository.create_debate(data)

    async def get_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> Optional[Debate]:
        """Get a debate by ID with all rounds and responses."""
        debate = self._repository.get_debate_by_id(debate_id)

        if debate is None:
            return None

        # Authorization check: verify ownership
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
        """List debates for a user with pagination."""
        return self._repository.list_debates(user_id, page, page_size, status)

    async def start_debate_stream(
        self,
        debate_id: str,
        user_id: str,
    ) -> AsyncIterator[DebateEvent]:
        """
        Start debate and stream events.

        Validates debate ownership and state, then delegates to
        DebateStreamAdapter for the actual execution.
        """
        from .stream_adapter import DebateStreamAdapter

        debate = await self.get_debate(debate_id, user_id)

        if debate is None:
            yield DebateEvent(
                type=DebateEventType.ERROR,
                debate_id=debate_id,
                error="Debate not found",
            )
            return

        if debate.status != DebateStatus.PENDING:
            yield DebateEvent(
                type=DebateEventType.ERROR,
                debate_id=debate_id,
                error=f"Debate already {debate.status.value}",
            )
            return

        # Create adapter and run
        adapter = DebateStreamAdapter(
            debate=debate,
            user_id=user_id,
            debate_service=self,
        )

        async for event in adapter.run():
            yield event

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

        return self._repository.delete(debate_id)

    async def update_debate_status(
        self,
        debate_id: str,
        status: DebateStatus,
        current_round: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update debate status and optionally current round or error message."""
        self._repository.update_status(debate_id, status, current_round, error_message)

    async def update_debate_totals(
        self,
        debate_id: str,
        total_input_tokens: int,
        total_output_tokens: int,
        total_cost: Decimal,
    ) -> None:
        """Update debate token and cost totals."""
        self._repository.update_totals(debate_id, total_input_tokens, total_output_tokens, total_cost)

    async def save_round(
        self,
        debate_id: str,
        round_number: int,
    ) -> str:
        """
        Create a new round record in the database.

        Returns:
            The ID of the created round.
        """
        return self._repository.save_round(debate_id, round_number)

    async def save_response(
        self,
        round_id: str,
        response: PersonalityResponse,
    ) -> str:
        """
        Save a personality response to the database.

        Returns:
            The ID of the created response.
        """
        return self._repository.save_response(round_id, response)

    async def save_synthesis(
        self,
        debate_id: str,
        content: str,
        input_tokens: int,
        output_tokens: int,
        cost: Decimal,
    ) -> str:
        """
        Save the debate synthesis to the database.

        Returns:
            The ID of the created synthesis.
        """
        return self._repository.save_synthesis(debate_id, content, input_tokens, output_tokens, cost)


# Module-level instance getter
_service_instance: Optional[DebateService] = None


def get_debate_service() -> DebateService:
    """Get the debate service singleton."""
    global _service_instance
    if _service_instance is None:
        from .repository import get_debate_repository
        _service_instance = DebateService(
            repository=get_debate_repository(),
        )
    return _service_instance


def reset_debate_service() -> None:
    """Reset the debate service singleton (for testing)."""
    global _service_instance
    _service_instance = None

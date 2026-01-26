"""
Debates module interface.

This is the core business logic interface for Prizms.
The API layer depends on IDebateService for all debate operations.
"""

from typing import Protocol, Optional, AsyncIterator, runtime_checkable

from .models import (
    Debate,
    DebateListResponse,
    CreateDebateRequest,
    DebateEvent,
    DebateStatus,
)


@runtime_checkable
class IDebateService(Protocol):
    """
    Interface for debate operations.

    This protocol defines the contract that the debates module exposes
    to the API layer and other modules.
    """

    async def create_debate(
        self,
        user_id: str,
        request: CreateDebateRequest,
    ) -> Debate:
        """
        Create a new debate.

        The debate is created in PENDING status. Call start_debate()
        or connect to the SSE stream to begin execution.

        Args:
            user_id: ID of the user creating the debate
            request: Debate configuration

        Returns:
            The created debate in PENDING status

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            ValidationError: If request is invalid
        """
        ...

    async def get_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> Optional[Debate]:
        """
        Get a debate by ID.

        Returns the full debate with all rounds and responses.

        Args:
            debate_id: Debate UUID
            user_id: User ID (for authorization check)

        Returns:
            Debate if found and authorized, None otherwise
        """
        ...

    async def list_debates(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[DebateStatus] = None,
    ) -> DebateListResponse:
        """
        List debates for a user.

        Returns paginated list of debates, most recent first.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page
            status: Optional status filter

        Returns:
            Paginated list of debate summaries
        """
        ...

    async def start_debate_stream(
        self,
        debate_id: str,
        user_id: str,
    ) -> AsyncIterator[DebateEvent]:
        """
        Start or resume a debate and stream events.

        This is the main entry point for debate execution. It:
        1. Validates the user has access and sufficient credits
        2. Updates status to ACTIVE
        3. Yields events as the debate progresses
        4. Updates status to COMPLETED or FAILED on finish

        Args:
            debate_id: Debate UUID
            user_id: User ID (for authorization)

        Yields:
            DebateEvent objects for each update

        Raises:
            NotFoundError: If debate doesn't exist
            AuthorizationError: If user doesn't own the debate
            InsufficientCreditsError: If user runs out of credits mid-debate
        """
        ...

    async def cancel_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> Debate:
        """
        Cancel an active debate.

        Only works for debates in PENDING or ACTIVE status.
        Credits for incomplete work are not refunded.

        Args:
            debate_id: Debate UUID
            user_id: User ID (for authorization)

        Returns:
            Updated debate with CANCELLED status

        Raises:
            NotFoundError: If debate doesn't exist
            AuthorizationError: If user doesn't own the debate
            ValidationError: If debate cannot be cancelled
        """
        ...

    async def delete_debate(
        self,
        debate_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a debate and all associated data.

        This is a soft delete - the debate is marked as deleted but
        retained for audit purposes.

        Args:
            debate_id: Debate UUID
            user_id: User ID (for authorization)

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If debate doesn't exist
            AuthorizationError: If user doesn't own the debate
        """
        ...

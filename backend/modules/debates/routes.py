"""
Debate API endpoints.

Provides REST endpoints for debate CRUD operations and SSE streaming.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from typing import Optional

from api.middleware.auth import get_current_user
from api.dependencies import get_debate_service
from shared.models import AuthenticatedUser

from .interfaces import IDebateService
from .models import (
    CreateDebateRequest,
    Debate,
    DebateListResponse,
    DebateStatus,
)
from .exceptions import DebateNotFoundError, DebateAccessDeniedError

router = APIRouter()


@router.post("", response_model=Debate, status_code=201)
async def create_debate(
    request: CreateDebateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: IDebateService = Depends(get_debate_service),
) -> Debate:
    """
    Create a new debate.

    The debate is created in 'pending' status. To start it,
    connect to the SSE stream endpoint (Story 14).
    """
    return await service.create_debate(user.id, request)


@router.get("", response_model=DebateListResponse)
async def list_debates(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[DebateStatus] = Query(default=None, description="Filter by status"),
    user: AuthenticatedUser = Depends(get_current_user),
    service: IDebateService = Depends(get_debate_service),
) -> DebateListResponse:
    """
    List the current user's debates.

    Returns paginated results, most recent first.
    Optionally filter by status.
    """
    return await service.list_debates(user.id, page, page_size, status)


@router.get("/{debate_id}", response_model=Debate)
async def get_debate(
    debate_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    service: IDebateService = Depends(get_debate_service),
) -> Debate:
    """
    Get a specific debate with all rounds and responses.
    """
    try:
        debate = await service.get_debate(debate_id, user.id)
        if not debate:
            raise HTTPException(status_code=404, detail="Debate not found")
        return debate
    except DebateAccessDeniedError:
        raise HTTPException(status_code=404, detail="Debate not found")


@router.post("/{debate_id}/cancel", response_model=Debate)
async def cancel_debate(
    debate_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    service: IDebateService = Depends(get_debate_service),
) -> Debate:
    """
    Cancel an active or pending debate.
    """
    try:
        return await service.cancel_debate(debate_id, user.id)
    except DebateNotFoundError:
        raise HTTPException(status_code=404, detail="Debate not found")
    except DebateAccessDeniedError:
        raise HTTPException(status_code=404, detail="Debate not found")


@router.delete("/{debate_id}", status_code=204)
async def delete_debate(
    debate_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    service: IDebateService = Depends(get_debate_service),
) -> None:
    """
    Delete a debate and all associated data.
    """
    try:
        await service.delete_debate(debate_id, user.id)
    except DebateNotFoundError:
        raise HTTPException(status_code=404, detail="Debate not found")
    except DebateAccessDeniedError:
        raise HTTPException(status_code=404, detail="Debate not found")


async def event_generator(
    debate_id: str,
    user_id: str,
    service: IDebateService,
):
    """
    Generate SSE events for a debate.

    Uses the DebateEvent.to_sse() method for formatting.

    Yields events in the format:
        event: <event_type>
        data: <json_data>
    """
    async for event in service.start_debate_stream(debate_id, user_id):
        yield {
            "event": event.type.value,
            "data": event.model_dump_json(exclude_none=True),
        }


@router.get("/{debate_id}/stream")
async def stream_debate(
    debate_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    service: IDebateService = Depends(get_debate_service),
):
    """
    Stream debate events via SSE.

    Connect to this endpoint to start a pending debate and receive
    real-time updates. The debate must be in 'pending' status.

    Event format:
        event: <event_type>
        data: {"type": "<type>", "debate_id": "...", "timestamp": "...", ...}

    Event types (from DebateEventType):

    Lifecycle:
    - debate_started: Debate has begun
    - debate_completed: Debate finished successfully
    - debate_failed: Debate failed with error

    Round:
    - round_started: New round starting
    - round_completed: Round finished

    Response:
    - personality_started: Personality beginning response
    - thinking_chunk: Chain-of-thought chunk (if extended thinking enabled)
    - answer_chunk: Answer content chunk
    - personality_completed: Personality finished with full response

    Synthesis:
    - synthesis_started: Synthesis beginning
    - synthesis_chunk: Synthesis content chunk
    - synthesis_completed: Synthesis finished

    Progress:
    - progress_update: General progress info
    - cost_update: Running cost total

    Error:
    - error: Non-fatal error occurred
    """
    return EventSourceResponse(
        event_generator(debate_id, user.id, service),
        media_type="text/event-stream",
    )

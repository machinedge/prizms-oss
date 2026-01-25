"""
Debate API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..middleware.auth import get_current_user
from ..models.user import AuthenticatedUser
from ..models.debate import (
    CreateDebateRequest,
    DebateResponse,
    DebateListResponse,
)
from ..services.debates import get_debate_service, DebateService

router = APIRouter()


@router.post("", response_model=DebateResponse, status_code=201)
async def create_debate(
    request: CreateDebateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: DebateService = Depends(get_debate_service),
) -> DebateResponse:
    """
    Create a new debate.

    The debate is created in 'pending' status. To start it,
    connect to the SSE stream endpoint.
    """
    # TODO: Check user credits before creating
    return await service.create_debate(user.id, request)


@router.get("", response_model=DebateListResponse)
async def list_debates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    service: DebateService = Depends(get_debate_service),
) -> DebateListResponse:
    """
    List the current user's debates.

    Returns paginated results, most recent first.
    """
    return await service.list_debates(user.id, page, page_size)


@router.get("/{debate_id}", response_model=DebateResponse)
async def get_debate(
    debate_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    service: DebateService = Depends(get_debate_service),
) -> DebateResponse:
    """
    Get a specific debate with all rounds and responses.
    """
    debate = await service.get_debate(debate_id, user.id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    return debate

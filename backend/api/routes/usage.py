"""
Usage tracking endpoints.

Provides endpoints for viewing usage statistics and history.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from shared.models import AuthenticatedUser
from ..middleware.auth import get_current_user
from api.dependencies import get_usage_service
from modules.usage.service import UsageService

router = APIRouter()


class UsageSummaryResponse(BaseModel):
    """Usage summary for current period."""

    period_start: datetime
    period_end: datetime
    total_tokens: int
    total_cost: float
    debates_count: int


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    user: AuthenticatedUser = Depends(get_current_user),
    service: UsageService = Depends(get_usage_service),
) -> UsageSummaryResponse:
    """
    Get usage summary for the current tracking period.

    Returns aggregated usage data including total tokens used,
    total cost, and number of debates for the current month.

    Requires authentication.
    """
    period_start, period_end = service.get_current_period()
    usage = await service.get_user_usage(user.id)

    return UsageSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        total_tokens=usage["total_tokens"],
        total_cost=float(usage["total_cost"]),
        debates_count=usage["debates_count"],
    )

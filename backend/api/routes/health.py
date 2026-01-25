"""
Health check endpoints.

Provides endpoints for monitoring application health and readiness.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    status: str
    database: str
    providers: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns 200 if the API is running.
    """
    return HealthResponse(status="healthy", version="0.1.0")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint.

    Checks if all dependencies are available.
    TODO: Add actual database and provider checks.
    """
    return ReadinessResponse(
        status="ready",
        database="connected",  # TODO: Actual check
        providers="available",  # TODO: Actual check
    )

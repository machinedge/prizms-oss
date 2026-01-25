"""
Debate models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DebateStatus(str, Enum):
    """Debate status enum."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class DebateSettings(BaseModel):
    """Configurable debate settings."""
    max_rounds: int = Field(default=3, ge=1, le=10)
    temperature: float = Field(default=0.7, ge=0, le=2)


class CreateDebateRequest(BaseModel):
    """Request to create a new debate."""
    question: str = Field(..., min_length=1, max_length=10000)
    provider: str = Field(..., description="Provider name (e.g., 'anthropic', 'openai')")
    model: str = Field(..., description="Model identifier (e.g., 'claude-3-5-sonnet')")
    settings: DebateSettings = Field(default_factory=DebateSettings)


class PersonalityResponse(BaseModel):
    """A single personality's response in a round."""
    personality_name: str
    thinking_content: Optional[str] = None
    answer_content: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0


class DebateRound(BaseModel):
    """A single round of the debate."""
    round_number: int
    responses: list[PersonalityResponse] = []
    created_at: datetime


class DebateSynthesis(BaseModel):
    """Final synthesis of the debate."""
    content: str
    tokens_used: int = 0
    cost: float = 0
    created_at: datetime


class DebateResponse(BaseModel):
    """Full debate response with all data."""
    id: str
    question: str
    status: DebateStatus
    provider: str
    model: str
    max_rounds: int
    current_round: int
    rounds: list[DebateRound] = []
    synthesis: Optional[DebateSynthesis] = None
    total_tokens: int = 0
    total_cost: float = 0
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class DebateListItem(BaseModel):
    """Summary item for debate list."""
    id: str
    question: str
    status: DebateStatus
    provider: str
    model: str
    current_round: int
    max_rounds: int
    total_cost: float = 0
    created_at: datetime


class DebateListResponse(BaseModel):
    """Paginated list of debates."""
    debates: list[DebateListItem]
    total: int
    page: int
    page_size: int
    has_more: bool

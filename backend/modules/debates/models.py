"""
Debates module data models.

These models define the core data structures for the Prizms debate system.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class DebateStatus(str, Enum):
    """Debate execution status."""

    PENDING = "pending"      # Created but not started
    ACTIVE = "active"        # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"        # Failed with error
    CANCELLED = "cancelled"  # Cancelled by user


class PersonalityType(str, Enum):
    """Built-in personality types."""

    OPTIMIST = "optimist"
    PESSIMIST = "pessimist"
    ANALYST = "analyst"
    CREATIVE = "creative"
    PRAGMATIST = "pragmatist"


# Default personalities for debates
DEFAULT_PERSONALITIES = [
    PersonalityType.OPTIMIST,
    PersonalityType.PESSIMIST,
    PersonalityType.ANALYST,
]


class DebateSettings(BaseModel):
    """Configurable debate settings."""

    max_rounds: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of debate rounds",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature setting",
    )
    personalities: list[str] = Field(
        default_factory=lambda: [p.value for p in DEFAULT_PERSONALITIES],
        description="Personality types to include",
    )
    include_synthesis: bool = Field(
        default=True,
        description="Whether to generate a synthesis at the end",
    )


class CreateDebateRequest(BaseModel):
    """Request to create a new debate."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The question or topic to debate",
    )
    provider: str = Field(
        ...,
        description="LLM provider (e.g., 'anthropic', 'openai')",
    )
    model: str = Field(
        ...,
        description="Model to use (e.g., 'claude-3-5-sonnet-20241022')",
    )
    settings: DebateSettings = Field(
        default_factory=DebateSettings,
        description="Debate settings",
    )


class PersonalityResponse(BaseModel):
    """A single personality's response in a round."""

    personality_name: str = Field(..., description="Personality type name")
    thinking_content: Optional[str] = Field(
        None,
        description="Extended thinking/reasoning (if enabled)",
    )
    answer_content: str = Field(..., description="The personality's response")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    cost: Decimal = Field(default=Decimal(0), description="Cost for this response")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the response was generated",
    )


class DebateRound(BaseModel):
    """A single round of the debate."""

    id: str = Field(..., description="Round ID (UUID)")
    debate_id: str = Field(..., description="Parent debate ID")
    round_number: int = Field(..., ge=1, description="Round number (1-indexed)")
    responses: list[PersonalityResponse] = Field(
        default_factory=list,
        description="Responses from each personality",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the round started",
    )


class DebateSynthesis(BaseModel):
    """Final synthesis combining all perspectives."""

    id: str = Field(..., description="Synthesis ID (UUID)")
    debate_id: str = Field(..., description="Parent debate ID")
    content: str = Field(..., description="Synthesis text")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    cost: Decimal = Field(default=Decimal(0), description="Cost for synthesis")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the synthesis was generated",
    )


class Debate(BaseModel):
    """
    Full debate with all data.

    This is the complete representation of a debate, including
    all rounds, responses, and synthesis.
    """

    id: str = Field(..., description="Debate ID (UUID)")
    user_id: str = Field(..., description="Owner user ID")
    question: str = Field(..., description="The debate question")
    status: DebateStatus = Field(..., description="Current status")
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model used")
    settings: DebateSettings = Field(..., description="Debate settings")

    # Progress
    current_round: int = Field(default=0, description="Current round number")
    max_rounds: int = Field(..., description="Maximum rounds")

    # Content
    rounds: list[DebateRound] = Field(
        default_factory=list,
        description="Completed rounds",
    )
    synthesis: Optional[DebateSynthesis] = Field(
        None,
        description="Final synthesis (if completed)",
    )

    # Costs
    total_input_tokens: int = Field(default=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, description="Total output tokens")
    total_cost: Decimal = Field(default=Decimal(0), description="Total cost")

    # Timestamps
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    started_at: Optional[datetime] = Field(None, description="When execution started")
    completed_at: Optional[datetime] = Field(None, description="When completed")

    # Error info
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DebateListItem(BaseModel):
    """Summary item for debate list (without full content)."""

    id: str = Field(..., description="Debate ID")
    question: str = Field(..., description="Debate question (may be truncated)")
    status: DebateStatus = Field(..., description="Current status")
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model used")
    current_round: int = Field(..., description="Current round")
    max_rounds: int = Field(..., description="Max rounds")
    total_cost: Decimal = Field(default=Decimal(0), description="Total cost")
    created_at: datetime = Field(..., description="Creation time")


class DebateListResponse(BaseModel):
    """Paginated list of debates."""

    debates: list[DebateListItem] = Field(..., description="Debate items")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")


# SSE Event Types

class DebateEventType(str, Enum):
    """Types of events emitted during debate streaming."""

    # Lifecycle events
    DEBATE_STARTED = "debate_started"
    DEBATE_COMPLETED = "debate_completed"
    DEBATE_FAILED = "debate_failed"

    # Round events
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"

    # Response events
    PERSONALITY_STARTED = "personality_started"
    THINKING_CHUNK = "thinking_chunk"      # Streaming thinking content
    ANSWER_CHUNK = "answer_chunk"          # Streaming answer content
    PERSONALITY_COMPLETED = "personality_completed"

    # Synthesis events
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_CHUNK = "synthesis_chunk"
    SYNTHESIS_COMPLETED = "synthesis_completed"

    # Progress events
    PROGRESS_UPDATE = "progress_update"    # General progress info
    COST_UPDATE = "cost_update"            # Running cost total

    # Error events
    ERROR = "error"


class DebateEvent(BaseModel):
    """
    Event emitted during debate streaming.

    These events are sent via SSE to the frontend to provide
    real-time updates during debate execution.
    """

    type: DebateEventType = Field(..., description="Event type")
    debate_id: str = Field(..., description="Debate ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp",
    )

    # Optional fields depending on event type
    round_number: Optional[int] = Field(None, description="Round number")
    personality: Optional[str] = Field(None, description="Personality name")
    content: Optional[str] = Field(None, description="Text content (for chunks)")
    response: Optional[PersonalityResponse] = Field(
        None,
        description="Complete response (for completed events)",
    )
    synthesis: Optional[DebateSynthesis] = Field(
        None,
        description="Synthesis (for synthesis_completed)",
    )
    progress: Optional[dict[str, Any]] = Field(
        None,
        description="Progress info",
    )
    cost: Optional[Decimal] = Field(None, description="Running cost")
    error: Optional[str] = Field(None, description="Error message")

    def to_sse(self) -> str:
        """Convert to SSE format."""
        import json
        data = self.model_dump(mode="json", exclude_none=True)
        return f"event: {self.type.value}\ndata: {json.dumps(data)}\n\n"

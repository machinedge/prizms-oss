"""
Usage tracking module data models.

These models define the data structures used by the usage module
and exposed to other modules through the interface.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ProviderPricing(BaseModel):
    """
    Pricing information for an LLM provider/model.

    Prices are per 1 million tokens (industry standard).
    """

    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model identifier")
    input_price_per_1m: Decimal = Field(
        ...,
        description="Price per 1M input tokens in USD",
    )
    output_price_per_1m: Decimal = Field(
        ...,
        description="Price per 1M output tokens in USD",
    )
    # Some providers charge differently for cached/extended thinking
    cached_input_price_per_1m: Optional[Decimal] = Field(
        None,
        description="Price per 1M cached input tokens (if applicable)",
    )

    model_config = {"frozen": True}

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> Decimal:
        """Calculate total cost for given token counts."""
        input_cost = (Decimal(input_tokens) / 1_000_000) * self.input_price_per_1m
        output_cost = (Decimal(output_tokens) / 1_000_000) * self.output_price_per_1m

        cached_cost = Decimal(0)
        if cached_tokens and self.cached_input_price_per_1m:
            cached_cost = (
                Decimal(cached_tokens) / 1_000_000
            ) * self.cached_input_price_per_1m

        return input_cost + output_cost + cached_cost


class UsageRecord(BaseModel):
    """
    A single usage record for an LLM operation.

    Created for each LLM API call during a debate.
    """

    id: Optional[str] = Field(None, description="Record ID (set after save)")
    user_id: str = Field(..., description="User ID")
    debate_id: Optional[str] = Field(None, description="Associated debate ID")

    # Provider info
    provider: str = Field(..., description="LLM provider (e.g., 'anthropic')")
    model: str = Field(..., description="Model used (e.g., 'claude-sonnet-4-5')")

    # Token counts
    input_tokens: int = Field(..., description="Input/prompt tokens")
    output_tokens: int = Field(..., description="Output/completion tokens")
    cached_tokens: int = Field(default=0, description="Cached input tokens")
    total_tokens: int = Field(default=0, description="Total tokens (computed)")

    # Cost
    cost: Decimal = Field(default=Decimal(0), description="Calculated cost in USD")

    # Metadata
    operation: str = Field(
        default="debate_response",
        description="Operation type (debate_response, synthesis, etc.)",
    )
    personality: Optional[str] = Field(None, description="Personality name if applicable")
    round_number: Optional[int] = Field(None, description="Debate round number")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the operation occurred",
    )

    @model_validator(mode="after")
    def compute_total_tokens(self) -> "UsageRecord":
        """Auto-compute total tokens if not set."""
        if self.total_tokens == 0:
            object.__setattr__(
                self,
                "total_tokens",
                self.input_tokens + self.output_tokens,
            )
        return self


class CostEstimate(BaseModel):
    """
    Estimated cost for an operation.

    Used before running an operation to check if user has enough credits.
    """

    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model name")
    input_tokens: int = Field(..., description="Estimated input tokens")
    output_tokens: int = Field(..., description="Estimated output tokens")

    # Cost breakdown
    input_cost: Decimal = Field(..., description="Cost for input tokens")
    output_cost: Decimal = Field(..., description="Cost for output tokens")
    total_cost: Decimal = Field(..., description="Total estimated cost")

    # Pricing used
    input_price_per_1m: Decimal = Field(..., description="Input price used")
    output_price_per_1m: Decimal = Field(..., description="Output price used")


class UsageSummary(BaseModel):
    """
    Aggregated usage summary for a time period.

    Used for dashboards and reports.
    """

    user_id: str = Field(..., description="User ID")
    start_date: Optional[datetime] = Field(None, description="Start of period")
    end_date: Optional[datetime] = Field(None, description="End of period")

    # Totals
    total_requests: int = Field(default=0, description="Total LLM requests")
    total_input_tokens: int = Field(default=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, description="Total output tokens")
    total_tokens: int = Field(default=0, description="Total tokens")
    total_cost: Decimal = Field(default=Decimal(0), description="Total cost")

    # Breakdown by provider
    by_provider: dict[str, dict] = Field(
        default_factory=dict,
        description="Usage breakdown by provider",
    )

    # Breakdown by operation type
    by_operation: dict[str, dict] = Field(
        default_factory=dict,
        description="Usage breakdown by operation type",
    )

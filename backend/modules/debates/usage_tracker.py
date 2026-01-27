"""
Usage tracker for debate token counting and cost calculation.

This module handles all usage-related tracking during debate execution,
including token counting, cost calculation, and running totals.
"""

from decimal import Decimal
from dataclasses import dataclass, field

from modules.usage.service import get_usage_service, UsageService
from modules.usage.models import UsageRecord
from modules.usage.token_counter import count_tokens


@dataclass
class UsageTotals:
    """Running totals for usage during a debate."""
    input_tokens: int = 0
    output_tokens: int = 0
    cost: Decimal = field(default_factory=lambda: Decimal(0))


class UsageTracker:
    """
    Tracks token usage and costs during debate execution.
    
    This class:
    - Counts tokens using tiktoken
    - Records usage via UsageService
    - Maintains running totals for the debate
    """
    
    def __init__(
        self,
        user_id: str,
        debate_id: str,
        provider: str,
        model: str,
        usage_service: UsageService | None = None,
    ):
        self.user_id = user_id
        self.debate_id = debate_id
        self.provider = provider
        self.model = model
        self._usage_service = usage_service or get_usage_service()
        self._totals = UsageTotals()
    
    @property
    def total_input_tokens(self) -> int:
        """Get total input tokens used."""
        return self._totals.input_tokens
    
    @property
    def total_output_tokens(self) -> int:
        """Get total output tokens used."""
        return self._totals.output_tokens
    
    @property
    def total_cost(self) -> Decimal:
        """Get total cost incurred."""
        return self._totals.cost
    
    def get_totals(self) -> UsageTotals:
        """Get a copy of the current usage totals."""
        return UsageTotals(
            input_tokens=self._totals.input_tokens,
            output_tokens=self._totals.output_tokens,
            cost=self._totals.cost,
        )
    
    async def record_personality_usage(
        self,
        personality: str,
        round_number: int,
        question: str,
        full_content: str,
    ) -> UsageRecord:
        """
        Record usage for a personality response.
        
        Args:
            personality: Name of the personality
            round_number: Current round number
            question: The debate question (for input token estimation)
            full_content: Full response content
            
        Returns:
            The recorded UsageRecord with calculated cost
        """
        # Count tokens using tiktoken
        # Input includes question + system prompt + prior context
        # We count the question tokens and add estimated prompt overhead
        question_tokens = count_tokens(question, self.model)
        input_tokens = question_tokens + 200  # 200 tokens for system prompt overhead
        output_tokens = count_tokens(full_content, self.model)
        
        # Record usage via service
        usage_record = await self._usage_service.record_usage(
            user_id=self.user_id,
            record=UsageRecord(
                user_id=self.user_id,
                debate_id=self.debate_id,
                provider=self.provider,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                operation="debate_response",
                personality=personality,
                round_number=round_number,
            ),
        )
        
        # Update running totals
        self._totals.input_tokens += usage_record.input_tokens
        self._totals.output_tokens += usage_record.output_tokens
        self._totals.cost += usage_record.cost
        
        return usage_record
    
    async def record_synthesis_usage(
        self,
        full_content: str,
    ) -> UsageRecord:
        """
        Record usage for synthesis.
        
        Args:
            full_content: Full synthesis content
            
        Returns:
            The recorded UsageRecord with calculated cost
        """
        # Count tokens using tiktoken
        # Input for synthesis includes all prior debate outputs + system prompt
        # We use accumulated output tokens as a proxy for context size
        input_tokens = self._totals.output_tokens + 500  # 500 for system prompt
        output_tokens = count_tokens(full_content, self.model)
        
        # Record usage via service
        usage_record = await self._usage_service.record_usage(
            user_id=self.user_id,
            record=UsageRecord(
                user_id=self.user_id,
                debate_id=self.debate_id,
                provider=self.provider,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                operation="synthesis",
            ),
        )
        
        # Update running totals
        self._totals.input_tokens += usage_record.input_tokens
        self._totals.output_tokens += usage_record.output_tokens
        self._totals.cost += usage_record.cost
        
        return usage_record

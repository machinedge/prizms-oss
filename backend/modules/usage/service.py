"""
Usage tracking service stub implementation.

This is a stub that will be completed in Story 15.
It provides a working in-memory implementation for testing.
"""

from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone
import uuid

from .interfaces import IUsageService, IPricingProvider
from .models import (
    UsageRecord,
    CostEstimate,
    UsageSummary,
    ProviderPricing,
)
from .pricing import get_pricing_provider, HybridPricingProvider


class UsageService:
    """
    Stub implementation of the usage service.

    Uses in-memory storage for testing. Will be replaced with
    Supabase implementation in Story 15.
    """

    def __init__(self, pricing_provider: Optional[IPricingProvider] = None):
        """
        Initialize the usage service.

        Args:
            pricing_provider: Optional pricing provider. If not provided,
                            uses the default HybridPricingProvider.
        """
        # In-memory storage for testing
        self._records: dict[str, list[UsageRecord]] = {}
        self._pricing_provider = pricing_provider or get_pricing_provider()

    def get_provider_pricing(self, provider: str, model: str) -> ProviderPricing:
        """Get pricing for a provider/model combination."""
        return self._pricing_provider.get_pricing_sync(provider, model)

    async def record_usage(
        self,
        user_id: str,
        record: UsageRecord,
    ) -> UsageRecord:
        """Record token usage for an LLM operation."""
        # Get pricing and calculate cost
        pricing = self.get_provider_pricing(record.provider, record.model)
        cost = pricing.calculate_cost(
            record.input_tokens,
            record.output_tokens,
            record.cached_tokens,
        )

        # Create complete record
        complete_record = UsageRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            debate_id=record.debate_id,
            provider=record.provider,
            model=record.model,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cached_tokens=record.cached_tokens,
            total_tokens=record.input_tokens + record.output_tokens,
            cost=cost,
            operation=record.operation,
            personality=record.personality,
            round_number=record.round_number,
            created_at=datetime.now(timezone.utc),
        )

        # Store in memory
        if user_id not in self._records:
            self._records[user_id] = []
        self._records[user_id].insert(0, complete_record)

        return complete_record

    async def estimate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostEstimate:
        """Estimate the cost of an operation."""
        pricing = self.get_provider_pricing(provider, model)

        input_cost = (Decimal(input_tokens) / 1_000_000) * pricing.input_price_per_1m
        output_cost = (Decimal(output_tokens) / 1_000_000) * pricing.output_price_per_1m

        return CostEstimate(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
            input_price_per_1m=pricing.input_price_per_1m,
            output_price_per_1m=pricing.output_price_per_1m,
        )

    async def get_usage_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[UsageRecord]:
        """Get a user's usage history."""
        records = self._records.get(user_id, [])

        # Filter by date if specified
        if start_date or end_date:
            filtered = []
            for record in records:
                if start_date and record.created_at < start_date:
                    continue
                if end_date and record.created_at > end_date:
                    continue
                filtered.append(record)
            records = filtered

        return records[offset : offset + limit]

    async def get_usage_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> UsageSummary:
        """Get aggregated usage summary."""
        records = await self.get_usage_history(
            user_id,
            limit=10000,  # Get all for aggregation
            start_date=start_date,
            end_date=end_date,
        )

        summary = UsageSummary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        by_provider: dict[str, dict] = {}
        by_operation: dict[str, dict] = {}

        for record in records:
            summary.total_requests += 1
            summary.total_input_tokens += record.input_tokens
            summary.total_output_tokens += record.output_tokens
            summary.total_tokens += record.total_tokens
            summary.total_cost += record.cost

            # Aggregate by provider
            if record.provider not in by_provider:
                by_provider[record.provider] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": Decimal(0),
                }
            by_provider[record.provider]["requests"] += 1
            by_provider[record.provider]["tokens"] += record.total_tokens
            by_provider[record.provider]["cost"] += record.cost

            # Aggregate by operation
            if record.operation not in by_operation:
                by_operation[record.operation] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": Decimal(0),
                }
            by_operation[record.operation]["requests"] += 1
            by_operation[record.operation]["tokens"] += record.total_tokens
            by_operation[record.operation]["cost"] += record.cost

        summary.by_provider = by_provider
        summary.by_operation = by_operation

        return summary


# Module-level instance getter
_service_instance: Optional[UsageService] = None


def get_usage_service() -> UsageService:
    """Get the usage service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = UsageService()
    return _service_instance


def reset_usage_service() -> None:
    """Reset the usage service singleton (for testing)."""
    global _service_instance
    _service_instance = None

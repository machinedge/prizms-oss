"""
Usage tracking module interface.

Other modules should depend on IUsageService, not the concrete implementation.
This enables the debates module to record usage without knowing pricing details.
"""

from typing import Protocol, Optional, runtime_checkable
from decimal import Decimal
from datetime import datetime

from .models import UsageRecord, CostEstimate, UsageSummary, ProviderPricing


@runtime_checkable
class IPricingProvider(Protocol):
    """
    Interface for fetching model pricing.

    This protocol defines the contract for pricing providers. Implementations
    can fetch pricing dynamically (e.g., from OpenRouter API) or use static
    hardcoded prices as a fallback.
    """

    async def get_pricing(self, provider: str, model: str) -> ProviderPricing:
        """
        Get pricing for a provider/model combination.

        Args:
            provider: LLM provider name (e.g., "anthropic", "openai")
            model: Model identifier (e.g., "claude-3-5-sonnet-20241022")

        Returns:
            ProviderPricing with per-token costs

        Raises:
            UnknownModelError: If provider/model combination is unknown
        """
        ...

    async def refresh_cache(self) -> None:
        """
        Force refresh of cached pricing data.

        Call this to ensure pricing data is up-to-date before
        critical cost calculations.
        """
        ...

    def get_pricing_sync(self, provider: str, model: str) -> ProviderPricing:
        """
        Synchronous version of get_pricing for contexts where async isn't available.

        Uses cached data only - does not fetch from external APIs.

        Args:
            provider: LLM provider name
            model: Model identifier

        Returns:
            ProviderPricing with per-token costs

        Raises:
            UnknownModelError: If provider/model combination is unknown
        """
        ...


@runtime_checkable
class IUsageService(Protocol):
    """
    Interface for usage tracking operations.

    This protocol defines the contract that the usage module exposes
    to other modules. The debates module uses this to record token usage.
    """

    async def record_usage(
        self,
        user_id: str,
        record: UsageRecord,
    ) -> UsageRecord:
        """
        Record token usage for an LLM operation.

        This is called after each LLM API call to track tokens used.
        The cost is automatically calculated based on provider pricing.

        Args:
            user_id: Supabase user ID
            record: Usage record with token counts

        Returns:
            The saved UsageRecord with calculated cost
        """
        ...

    async def estimate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostEstimate:
        """
        Estimate the cost of an operation before running it.

        Used by the debates module to check if user has enough credits
        before starting a debate.

        Args:
            provider: LLM provider name (e.g., "anthropic")
            model: Model identifier (e.g., "claude-3-5-sonnet-20241022")
            input_tokens: Estimated input token count
            output_tokens: Estimated output token count

        Returns:
            CostEstimate with breakdown by token type
        """
        ...

    async def get_usage_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[UsageRecord]:
        """
        Get a user's usage history.

        Args:
            user_id: Supabase user ID
            limit: Maximum records to return
            offset: Records to skip
            start_date: Optional start of date range
            end_date: Optional end of date range

        Returns:
            List of usage records, most recent first
        """
        ...

    async def get_usage_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> UsageSummary:
        """
        Get aggregated usage summary for a user.

        Useful for displaying usage dashboards and reports.

        Args:
            user_id: Supabase user ID
            start_date: Optional start of date range
            end_date: Optional end of date range

        Returns:
            Aggregated usage summary
        """
        ...

    def get_provider_pricing(self, provider: str, model: str) -> ProviderPricing:
        """
        Get pricing information for a provider/model combination.

        This is a synchronous method since pricing is typically cached.

        Args:
            provider: LLM provider name
            model: Model identifier

        Returns:
            ProviderPricing with per-token costs

        Raises:
            UnknownModelError: If provider/model combination is unknown
        """
        ...

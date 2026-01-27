"""
Usage tracking service implementation.

Provides both in-memory (for testing) and Supabase-backed (for production)
implementations of usage tracking.
"""

from decimal import Decimal
from typing import Optional, Any
from datetime import datetime, timezone
import uuid

from dateutil.relativedelta import relativedelta

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
    Usage tracking service with in-memory storage.

    For testing and development. Use SupabaseUsageService for production.
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

    def get_current_period(self) -> tuple[datetime, datetime]:
        """
        Get the current tracking period (monthly).

        Returns:
            Tuple of (period_start, period_end) datetimes
        """
        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + relativedelta(months=1)
        return period_start, period_end

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

    async def get_user_usage(
        self,
        user_id: str,
        period_start: Optional[datetime] = None,
    ) -> dict:
        """
        Get usage for a user in a specific period.

        Args:
            user_id: User ID
            period_start: Optional period start (defaults to current)

        Returns:
            Usage dict with total_tokens, total_cost, debates_count
        """
        if period_start is None:
            period_start, period_end = self.get_current_period()
        else:
            period_end = period_start + relativedelta(months=1)

        records = self._records.get(user_id, [])
        filtered = [
            r for r in records
            if r.created_at >= period_start and r.created_at < period_end
        ]

        total_tokens = sum(r.total_tokens for r in filtered)
        total_cost = sum(r.cost for r in filtered)
        debate_ids = set(r.debate_id for r in filtered if r.debate_id)

        return {
            "total_tokens": total_tokens,
            "total_cost": float(total_cost),
            "debates_count": len(debate_ids),
        }

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


class SupabaseUsageService(UsageService):
    """
    Usage service with Supabase persistence.

    Extends the base UsageService to store records in Supabase
    while maintaining the same interface.
    """

    def __init__(
        self,
        supabase_client: Any,
        pricing_provider: Optional[IPricingProvider] = None,
    ):
        """
        Initialize with Supabase client.

        Args:
            supabase_client: Supabase client instance
            pricing_provider: Optional pricing provider
        """
        super().__init__(pricing_provider)
        self._db = supabase_client

    async def record_usage(
        self,
        user_id: str,
        record: UsageRecord,
    ) -> UsageRecord:
        """Record usage with database persistence."""
        pricing = self.get_provider_pricing(record.provider, record.model)
        cost = pricing.calculate_cost(
            record.input_tokens,
            record.output_tokens,
            record.cached_tokens,
        )

        record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Insert into usage_log
        self._db.table("usage_log").insert({
            "id": record_id,
            "user_id": user_id,
            "debate_id": record.debate_id,
            "provider": record.provider,
            "model": record.model,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "cached_tokens": record.cached_tokens or 0,
            "cost": float(cost),
            "operation": record.operation,
            "personality": record.personality,
            "round_number": record.round_number,
            "created_at": now.isoformat(),
        }).execute()

        # Update period aggregate using RPC
        period_start, period_end = self.get_current_period()
        self._db.rpc("upsert_user_usage", {
            "p_user_id": user_id,
            "p_period_start": period_start.isoformat(),
            "p_period_end": period_end.isoformat(),
            "p_tokens": record.input_tokens + record.output_tokens,
            "p_cost": float(cost),
            "p_increment_debates": False,
        }).execute()

        return UsageRecord(
            id=record_id,
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
            created_at=now,
        )

    async def get_user_usage(
        self,
        user_id: str,
        period_start: Optional[datetime] = None,
    ) -> dict:
        """Get usage from database."""
        if period_start is None:
            period_start, _ = self.get_current_period()

        result = self._db.table("user_usage").select("*").eq(
            "user_id", user_id
        ).eq(
            "period_start", period_start.isoformat()
        ).execute()

        if result.data:
            row = result.data[0]
            return {
                "total_tokens": row.get("total_tokens", 0),
                "total_cost": float(row.get("total_cost", 0)),
                "debates_count": row.get("debates_count", 0),
            }

        return {
            "total_tokens": 0,
            "total_cost": 0.0,
            "debates_count": 0,
        }

    async def get_usage_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[UsageRecord]:
        """Get usage history from database."""
        query = self._db.table("usage_log").select("*").eq("user_id", user_id)

        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", end_date.isoformat())

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        return [
            UsageRecord(
                id=r["id"],
                user_id=r["user_id"],
                debate_id=r.get("debate_id"),
                provider=r["provider"],
                model=r["model"],
                input_tokens=r["input_tokens"],
                output_tokens=r["output_tokens"],
                cached_tokens=r.get("cached_tokens", 0),
                total_tokens=r["input_tokens"] + r["output_tokens"],
                cost=Decimal(str(r["cost"])),
                operation=r.get("operation"),
                personality=r.get("personality"),
                round_number=r.get("round_number"),
                created_at=datetime.fromisoformat(
                    r["created_at"].replace("Z", "+00:00")
                ),
            )
            for r in result.data
        ]



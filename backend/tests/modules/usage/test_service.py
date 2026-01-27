"""Tests for usage service."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from modules.usage.service import UsageService, reset_usage_service
from modules.usage.models import UsageRecord
from modules.usage.pricing import StaticPricingProvider


class TestUsageService:
    # Note: Tests use the `usage_service` fixture from conftest.py

    @pytest.mark.asyncio
    async def test_record_usage(self, usage_service):
        """Should record usage with calculated cost."""
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )

        saved = await usage_service.record_usage("user-123", record)

        assert saved.id is not None
        assert saved.cost > Decimal(0)
        assert saved.total_tokens == 1500
        assert saved.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_record_usage_with_metadata(self, usage_service):
        """Should preserve metadata in saved record."""
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
            debate_id="debate-456",
            operation="synthesis",
            personality="Optimist",
            round_number=2,
        )

        saved = await usage_service.record_usage("user-123", record)

        assert saved.debate_id == "debate-456"
        assert saved.operation == "synthesis"
        assert saved.personality == "Optimist"
        assert saved.round_number == 2

    @pytest.mark.asyncio
    async def test_estimate_cost(self, usage_service):
        """Should estimate cost correctly."""
        estimate = await usage_service.estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=10000,
            output_tokens=5000,
        )

        assert estimate.total_cost > Decimal(0)
        assert estimate.input_cost > Decimal(0)
        assert estimate.output_cost > Decimal(0)
        assert estimate.total_cost == estimate.input_cost + estimate.output_cost

    @pytest.mark.asyncio
    async def test_estimate_cost_breakdown(self, usage_service):
        """Should provide correct cost breakdown."""
        estimate = await usage_service.estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1_000_000,  # 1M tokens
            output_tokens=500_000,   # 0.5M tokens
        )

        # Claude Sonnet 4.5: $3/M input, $15/M output
        assert estimate.input_cost == Decimal("3.00")
        assert estimate.output_cost == Decimal("7.50")
        assert estimate.total_cost == Decimal("10.50")

    @pytest.mark.asyncio
    async def test_usage_history_empty(self, usage_service):
        """Should return empty list for new user."""
        history = await usage_service.get_usage_history("new-user")
        assert history == []

    @pytest.mark.asyncio
    async def test_usage_history(self, usage_service):
        """Should track usage history."""
        record1 = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        record2 = UsageRecord(
            user_id="user-123",
            provider="openai",
            model="gpt-4o",
            input_tokens=2000,
            output_tokens=1000,
        )

        await usage_service.record_usage("user-123", record1)
        await usage_service.record_usage("user-123", record2)

        history = await usage_service.get_usage_history("user-123")
        assert len(history) == 2
        # Most recent first
        assert history[0].provider == "openai"
        assert history[1].provider == "anthropic"

    @pytest.mark.asyncio
    async def test_usage_history_limit(self, usage_service):
        """Should respect limit parameter."""
        for i in range(10):
            record = UsageRecord(
                user_id="user-123",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=100,
                output_tokens=50,
            )
            await usage_service.record_usage("user-123", record)

        history = await usage_service.get_usage_history("user-123", limit=5)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_usage_history_offset(self, usage_service):
        """Should respect offset parameter."""
        for i in range(10):
            record = UsageRecord(
                user_id="user-123",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=100 * (i + 1),
                output_tokens=50,
            )
            await usage_service.record_usage("user-123", record)

        # Get records 5-9 (offset 5, limit 5)
        history = await usage_service.get_usage_history("user-123", limit=5, offset=5)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_usage_history_per_user(self, usage_service):
        """Should only return usage for specific user."""
        record1 = UsageRecord(
            user_id="user-1",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        record2 = UsageRecord(
            user_id="user-2",
            provider="openai",
            model="gpt-4o",
            input_tokens=2000,
            output_tokens=1000,
        )

        await usage_service.record_usage("user-1", record1)
        await usage_service.record_usage("user-2", record2)

        history1 = await usage_service.get_usage_history("user-1")
        history2 = await usage_service.get_usage_history("user-2")

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0].provider == "anthropic"
        assert history2[0].provider == "openai"

    @pytest.mark.asyncio
    async def test_usage_summary_empty(self, usage_service):
        """Should return empty summary for new user."""
        summary = await usage_service.get_usage_summary("new-user")
        assert summary.total_requests == 0
        assert summary.total_tokens == 0
        assert summary.total_cost == Decimal(0)

    @pytest.mark.asyncio
    async def test_usage_summary(self, usage_service):
        """Should aggregate usage summary."""
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        await usage_service.record_usage("user-123", record)

        summary = await usage_service.get_usage_summary("user-123")
        assert summary.total_requests == 1
        assert summary.total_tokens == 1500
        assert summary.total_cost > Decimal(0)

    @pytest.mark.asyncio
    async def test_usage_summary_multiple_records(self, usage_service):
        """Should aggregate multiple records."""
        record1 = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        record2 = UsageRecord(
            user_id="user-123",
            provider="openai",
            model="gpt-4o",
            input_tokens=2000,
            output_tokens=1000,
        )

        await usage_service.record_usage("user-123", record1)
        await usage_service.record_usage("user-123", record2)

        summary = await usage_service.get_usage_summary("user-123")
        assert summary.total_requests == 2
        assert summary.total_input_tokens == 3000
        assert summary.total_output_tokens == 1500
        assert summary.total_tokens == 4500

    @pytest.mark.asyncio
    async def test_usage_summary_by_provider(self, usage_service):
        """Should group usage by provider."""
        for _ in range(3):
            await usage_service.record_usage("user-123", UsageRecord(
                user_id="user-123",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=100,
                output_tokens=50,
            ))
        for _ in range(2):
            await usage_service.record_usage("user-123", UsageRecord(
                user_id="user-123",
                provider="openai",
                model="gpt-4o",
                input_tokens=200,
                output_tokens=100,
            ))

        summary = await usage_service.get_usage_summary("user-123")
        assert "anthropic" in summary.by_provider
        assert "openai" in summary.by_provider
        assert summary.by_provider["anthropic"]["requests"] == 3
        assert summary.by_provider["openai"]["requests"] == 2

    @pytest.mark.asyncio
    async def test_usage_summary_by_operation(self, usage_service):
        """Should group usage by operation."""
        await usage_service.record_usage("user-123", UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=100,
            output_tokens=50,
            operation="debate_response",
        ))
        await usage_service.record_usage("user-123", UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=200,
            output_tokens=100,
            operation="synthesis",
        ))

        summary = await usage_service.get_usage_summary("user-123")
        assert "debate_response" in summary.by_operation
        assert "synthesis" in summary.by_operation

    def test_get_provider_pricing(self, usage_service):
        """Should return pricing for known provider/model."""
        pricing = usage_service.get_provider_pricing("anthropic", "claude-sonnet-4-5")
        assert pricing.provider == "anthropic"
        assert pricing.input_price_per_1m == Decimal("3.00")
        assert pricing.output_price_per_1m == Decimal("15.00")

    def test_get_provider_pricing_unknown(self, usage_service):
        """Should return default pricing for unknown model."""
        pricing = usage_service.get_provider_pricing("unknown", "unknown-model")
        assert pricing.provider == "unknown"

    def test_get_current_period(self, usage_service):
        """Should return current month boundaries."""
        period_start, period_end = usage_service.get_current_period()
        
        # Period start should be first day of month
        assert period_start.day == 1
        assert period_start.hour == 0
        assert period_start.minute == 0
        assert period_start.second == 0
        
        # Period end should be first day of next month
        assert period_end.day == 1
        assert period_end > period_start

    def test_get_current_period_timezone(self, usage_service):
        """Should return UTC datetimes."""
        period_start, period_end = usage_service.get_current_period()
        
        assert period_start.tzinfo is not None
        assert period_end.tzinfo is not None

    @pytest.mark.asyncio
    async def test_get_user_usage_empty(self, usage_service):
        """Should return zeros for user with no usage."""
        usage = await usage_service.get_user_usage("no-usage-user")
        
        assert usage["total_tokens"] == 0
        assert usage["total_cost"] == 0.0
        assert usage["debates_count"] == 0

    @pytest.mark.asyncio
    async def test_get_user_usage_with_records(self, usage_service):
        """Should aggregate usage for current period."""
        # Record some usage
        for i in range(3):
            await usage_service.record_usage("user-123", UsageRecord(
                user_id="user-123",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=1000,
                output_tokens=500,
                debate_id=f"debate-{i}",
            ))
        
        usage = await usage_service.get_user_usage("user-123")
        
        assert usage["total_tokens"] == 4500  # 3 * (1000 + 500)
        assert usage["total_cost"] > 0
        assert usage["debates_count"] == 3

    @pytest.mark.asyncio
    async def test_get_user_usage_same_debate(self, usage_service):
        """Should count unique debates only."""
        # Record multiple usage records for same debate
        for _ in range(5):
            await usage_service.record_usage("user-123", UsageRecord(
                user_id="user-123",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=100,
                output_tokens=50,
                debate_id="same-debate",
            ))
        
        usage = await usage_service.get_user_usage("user-123")
        
        assert usage["debates_count"] == 1  # Only one unique debate

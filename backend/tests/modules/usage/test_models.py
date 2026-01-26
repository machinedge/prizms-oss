"""Tests for usage module models."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from modules.usage.models import (
    UsageRecord,
    CostEstimate,
    UsageSummary,
    ProviderPricing,
)


class TestProviderPricing:
    def test_create_pricing(self):
        """Should create provider pricing."""
        pricing = ProviderPricing(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_price_per_1m=Decimal("3.00"),
            output_price_per_1m=Decimal("15.00"),
        )
        assert pricing.provider == "anthropic"
        assert pricing.model == "claude-sonnet-4-5"
        assert pricing.input_price_per_1m == Decimal("3.00")
        assert pricing.output_price_per_1m == Decimal("15.00")

    def test_optional_cached_pricing(self):
        """Cached pricing should be optional."""
        pricing = ProviderPricing(
            provider="openai",
            model="gpt-4o",
            input_price_per_1m=Decimal("2.50"),
            output_price_per_1m=Decimal("10.00"),
        )
        assert pricing.cached_input_price_per_1m is None

    def test_calculate_cost_basic(self):
        """Should calculate cost correctly for basic tokens."""
        pricing = ProviderPricing(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_price_per_1m=Decimal("3.00"),
            output_price_per_1m=Decimal("15.00"),
        )

        # 1000 input + 500 output tokens
        cost = pricing.calculate_cost(1000, 500)

        # Expected: (1000/1M * 3) + (500/1M * 15) = 0.003 + 0.0075 = 0.0105
        assert cost == Decimal("0.0105")

    def test_calculate_cost_with_cached(self):
        """Should include cached tokens in cost calculation."""
        pricing = ProviderPricing(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_price_per_1m=Decimal("3.00"),
            output_price_per_1m=Decimal("15.00"),
            cached_input_price_per_1m=Decimal("0.30"),
        )

        # 1000 input + 500 output + 2000 cached tokens
        cost = pricing.calculate_cost(1000, 500, 2000)

        # Expected: 0.003 + 0.0075 + (2000/1M * 0.30) = 0.0105 + 0.0006 = 0.0111
        assert cost == Decimal("0.0111")

    def test_calculate_cost_large_tokens(self):
        """Should handle large token counts."""
        pricing = ProviderPricing(
            provider="openai",
            model="gpt-4o-mini",
            input_price_per_1m=Decimal("0.15"),
            output_price_per_1m=Decimal("0.60"),
        )

        # 100,000 input + 50,000 output tokens
        cost = pricing.calculate_cost(100_000, 50_000)

        # Expected: (100000/1M * 0.15) + (50000/1M * 0.60) = 0.015 + 0.03 = 0.045
        assert cost == Decimal("0.045")

    def test_pricing_is_frozen(self):
        """Pricing should be immutable (frozen)."""
        pricing = ProviderPricing(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_price_per_1m=Decimal("3.00"),
            output_price_per_1m=Decimal("15.00"),
        )
        with pytest.raises(Exception):  # Pydantic validation error
            pricing.input_price_per_1m = Decimal("5.00")


class TestUsageRecord:
    def test_create_usage_record(self):
        """Should create a usage record."""
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        assert record.user_id == "user-123"
        assert record.provider == "anthropic"
        assert record.model == "claude-sonnet-4-5"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500

    def test_auto_compute_total_tokens(self):
        """Should auto-compute total tokens."""
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        assert record.total_tokens == 1500

    def test_default_values(self):
        """Should have correct default values."""
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        assert record.id is None
        assert record.debate_id is None
        assert record.cached_tokens == 0
        assert record.cost == Decimal(0)
        assert record.operation == "debate_response"
        assert record.personality is None
        assert record.round_number is None

    def test_optional_metadata(self):
        """Should accept optional metadata."""
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
            debate_id="debate-456",
            operation="synthesis",
            personality="Devil's Advocate",
            round_number=3,
        )
        assert record.debate_id == "debate-456"
        assert record.operation == "synthesis"
        assert record.personality == "Devil's Advocate"
        assert record.round_number == 3

    def test_created_at_default(self):
        """Should default created_at to current time."""
        before = datetime.now(timezone.utc)
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        after = datetime.now(timezone.utc)
        assert before <= record.created_at <= after


class TestCostEstimate:
    def test_create_cost_estimate(self):
        """Should create a cost estimate."""
        estimate = CostEstimate(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=10000,
            output_tokens=5000,
            input_cost=Decimal("0.03"),
            output_cost=Decimal("0.075"),
            total_cost=Decimal("0.105"),
            input_price_per_1m=Decimal("3.00"),
            output_price_per_1m=Decimal("15.00"),
        )
        assert estimate.total_cost == Decimal("0.105")
        assert estimate.input_tokens == 10000
        assert estimate.output_tokens == 5000


class TestUsageSummary:
    def test_create_usage_summary(self):
        """Should create a usage summary."""
        summary = UsageSummary(
            user_id="user-123",
        )
        assert summary.user_id == "user-123"
        assert summary.total_requests == 0
        assert summary.total_tokens == 0
        assert summary.total_cost == Decimal(0)

    def test_optional_date_range(self):
        """Date range should be optional."""
        summary = UsageSummary(user_id="user-123")
        assert summary.start_date is None
        assert summary.end_date is None

    def test_summary_with_dates(self):
        """Should accept date range."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        summary = UsageSummary(
            user_id="user-123",
            start_date=start,
            end_date=end,
        )
        assert summary.start_date == start
        assert summary.end_date == end

    def test_breakdown_dicts(self):
        """Should have empty breakdown dicts by default."""
        summary = UsageSummary(user_id="user-123")
        assert summary.by_provider == {}
        assert summary.by_operation == {}


class TestProviderPricingFixture:
    """Tests that verify test pricing fixtures work correctly."""

    def test_test_pricing_data_has_anthropic(self, test_pricing_data):
        """Test pricing fixture should have Anthropic data."""
        assert "anthropic" in test_pricing_data
        assert "claude-sonnet-4-5" in test_pricing_data["anthropic"]

    def test_test_pricing_data_has_openai(self, test_pricing_data):
        """Test pricing fixture should have OpenAI data."""
        assert "openai" in test_pricing_data
        assert "gpt-4o" in test_pricing_data["openai"]
        assert "gpt-4o-mini" in test_pricing_data["openai"]

    def test_test_pricing_data_has_google(self, test_pricing_data):
        """Test pricing fixture should have Google data."""
        assert "google" in test_pricing_data
        assert "gemini-2.0-flash" in test_pricing_data["google"]

    def test_test_pricing_data_has_xai(self, test_pricing_data):
        """Test pricing fixture should have xAI data."""
        assert "xai" in test_pricing_data
        assert "grok-4" in test_pricing_data["xai"]

    def test_default_pricing_fixture(self, default_pricing):
        """Default pricing fixture should have expected values."""
        assert default_pricing.provider == "unknown"
        assert default_pricing.model == "unknown"
        assert default_pricing.input_price_per_1m == Decimal("5.00")
        assert default_pricing.output_price_per_1m == Decimal("15.00")

    def test_pricing_values_reasonable(self, test_pricing_data):
        """Pricing values should be reasonable (positive, not too high)."""
        for provider, models in test_pricing_data.items():
            for model, pricing in models.items():
                assert pricing.input_price_per_1m > 0
                assert pricing.output_price_per_1m > 0
                # Sanity check: no price should exceed $100/M tokens
                assert pricing.input_price_per_1m <= Decimal("100.00")
                assert pricing.output_price_per_1m <= Decimal("100.00")

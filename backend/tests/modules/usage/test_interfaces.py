"""Tests for usage module interfaces."""

import pytest
from decimal import Decimal

from modules.usage.interfaces import IUsageService, IPricingProvider
from modules.usage.service import UsageService
from modules.usage.pricing import (
    StaticPricingProvider,
    OpenRouterPricingProvider,
    HybridPricingProvider,
)
from modules.usage.models import UsageRecord


class TestIPricingProviderProtocol:
    def test_static_pricing_implements_protocol(self, test_pricing_data, default_pricing):
        """StaticPricingProvider should implement IPricingProvider."""
        provider = StaticPricingProvider(test_pricing_data, default_pricing)
        assert isinstance(provider, IPricingProvider)

    def test_openrouter_pricing_implements_protocol(self):
        """OpenRouterPricingProvider should implement IPricingProvider."""
        provider = OpenRouterPricingProvider()
        assert isinstance(provider, IPricingProvider)

    def test_hybrid_pricing_implements_protocol(self, test_pricing_data, default_pricing):
        """HybridPricingProvider should implement IPricingProvider."""
        provider = HybridPricingProvider(
            static_pricing_data=test_pricing_data,
            default_pricing=default_pricing,
        )
        assert isinstance(provider, IPricingProvider)


class TestIUsageServiceProtocol:
    def test_usage_service_implements_protocol(self, usage_service):
        """UsageService should implement IUsageService."""
        assert isinstance(usage_service, IUsageService)


class TestPricingProviderContract:
    """Test that all pricing providers fulfill the contract."""

    @pytest.fixture(params=["static", "openrouter", "hybrid"])
    def provider(self, request, test_pricing_data, default_pricing):
        """Parameterized fixture for all pricing providers."""
        if request.param == "static":
            return StaticPricingProvider(test_pricing_data, default_pricing)
        elif request.param == "openrouter":
            return OpenRouterPricingProvider(api_key=None, fallback_pricing=default_pricing)
        else:  # hybrid
            return HybridPricingProvider(
                openrouter_api_key=None,
                static_pricing_data=test_pricing_data,
                default_pricing=default_pricing,
            )

    @pytest.mark.asyncio
    async def test_get_pricing_returns_provider_pricing(self, provider):
        """get_pricing should return ProviderPricing object."""
        from modules.usage.models import ProviderPricing
        pricing = await provider.get_pricing("anthropic", "claude-sonnet-4-5")
        assert isinstance(pricing, ProviderPricing)

    @pytest.mark.asyncio
    async def test_refresh_cache_doesnt_raise(self, provider):
        """refresh_cache should not raise exceptions."""
        # Should complete without raising
        await provider.refresh_cache()

    def test_get_pricing_sync_returns_provider_pricing(self, provider):
        """get_pricing_sync should return ProviderPricing object."""
        from modules.usage.models import ProviderPricing
        pricing = provider.get_pricing_sync("openai", "gpt-4o")
        assert isinstance(pricing, ProviderPricing)


class TestUsageServiceContract:
    """Test that UsageService fulfills the IUsageService contract."""

    @pytest.mark.asyncio
    async def test_record_usage_returns_usage_record(self, usage_service):
        """record_usage should return UsageRecord."""
        record = UsageRecord(
            user_id="user-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=100,
            output_tokens=50,
        )
        result = await usage_service.record_usage("user-123", record)
        assert isinstance(result, UsageRecord)
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_estimate_cost_returns_cost_estimate(self, usage_service):
        """estimate_cost should return CostEstimate."""
        from modules.usage.models import CostEstimate
        estimate = await usage_service.estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        assert isinstance(estimate, CostEstimate)

    @pytest.mark.asyncio
    async def test_get_usage_history_returns_list(self, usage_service):
        """get_usage_history should return list of UsageRecord."""
        history = await usage_service.get_usage_history("user-123")
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_get_usage_summary_returns_summary(self, usage_service):
        """get_usage_summary should return UsageSummary."""
        from modules.usage.models import UsageSummary
        summary = await usage_service.get_usage_summary("user-123")
        assert isinstance(summary, UsageSummary)

    def test_get_provider_pricing_returns_pricing(self, usage_service):
        """get_provider_pricing should return ProviderPricing."""
        from modules.usage.models import ProviderPricing
        pricing = usage_service.get_provider_pricing("anthropic", "claude-sonnet-4-5")
        assert isinstance(pricing, ProviderPricing)

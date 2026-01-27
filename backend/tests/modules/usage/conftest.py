"""
Pytest fixtures for usage module tests.

Provides test pricing data that would normally come from Supabase in production.
"""

import pytest
from decimal import Decimal

from modules.usage.models import ProviderPricing


@pytest.fixture
def default_pricing():
    """Default pricing for unknown models."""
    return ProviderPricing(
        provider="unknown",
        model="unknown",
        input_price_per_1m=Decimal("5.00"),
        output_price_per_1m=Decimal("15.00"),
    )


@pytest.fixture
def test_pricing_data():
    """
    Test pricing data for usage module tests.
    
    This data would normally be loaded from Supabase in production.
    """
    return {
        "anthropic": {
            "claude-sonnet-4-5": ProviderPricing(
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_price_per_1m=Decimal("3.00"),
                output_price_per_1m=Decimal("15.00"),
                cached_input_price_per_1m=Decimal("0.30"),
            ),
            "claude-opus-4-5": ProviderPricing(
                provider="anthropic",
                model="claude-opus-4-5",
                input_price_per_1m=Decimal("5.00"),
                output_price_per_1m=Decimal("25.00"),
                cached_input_price_per_1m=Decimal("0.50"),
            ),
            "claude-haiku-4-5": ProviderPricing(
                provider="anthropic",
                model="claude-haiku-4-5",
                input_price_per_1m=Decimal("1.00"),
                output_price_per_1m=Decimal("5.00"),
                cached_input_price_per_1m=Decimal("0.10"),
            ),
            # Legacy models
            "claude-3-5-sonnet-20241022": ProviderPricing(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                input_price_per_1m=Decimal("3.00"),
                output_price_per_1m=Decimal("15.00"),
                cached_input_price_per_1m=Decimal("0.30"),
            ),
        },
        "openai": {
            "gpt-4o": ProviderPricing(
                provider="openai",
                model="gpt-4o",
                input_price_per_1m=Decimal("2.50"),
                output_price_per_1m=Decimal("10.00"),
            ),
            "gpt-4o-mini": ProviderPricing(
                provider="openai",
                model="gpt-4o-mini",
                input_price_per_1m=Decimal("0.15"),
                output_price_per_1m=Decimal("0.60"),
            ),
            "gpt-5-mini": ProviderPricing(
                provider="openai",
                model="gpt-5-mini",
                input_price_per_1m=Decimal("0.25"),
                output_price_per_1m=Decimal("2.00"),
            ),
            "gpt-5.2": ProviderPricing(
                provider="openai",
                model="gpt-5.2",
                input_price_per_1m=Decimal("1.75"),
                output_price_per_1m=Decimal("14.00"),
            ),
        },
        "google": {
            "gemini-2.0-flash": ProviderPricing(
                provider="google",
                model="gemini-2.0-flash",
                input_price_per_1m=Decimal("0.10"),
                output_price_per_1m=Decimal("0.40"),
            ),
            "gemini-1.5-pro": ProviderPricing(
                provider="google",
                model="gemini-1.5-pro",
                input_price_per_1m=Decimal("1.25"),
                output_price_per_1m=Decimal("5.00"),
            ),
            "gemini-1.5-flash": ProviderPricing(
                provider="google",
                model="gemini-1.5-flash",
                input_price_per_1m=Decimal("0.075"),
                output_price_per_1m=Decimal("0.30"),
            ),
        },
        "xai": {
            "grok-4": ProviderPricing(
                provider="xai",
                model="grok-4",
                input_price_per_1m=Decimal("3.00"),
                output_price_per_1m=Decimal("15.00"),
                cached_input_price_per_1m=Decimal("0.75"),
            ),
            "grok-4-fast": ProviderPricing(
                provider="xai",
                model="grok-4-fast",
                input_price_per_1m=Decimal("0.20"),
                output_price_per_1m=Decimal("0.50"),
            ),
            # Legacy models
            "grok-3": ProviderPricing(
                provider="xai",
                model="grok-3",
                input_price_per_1m=Decimal("2.00"),
                output_price_per_1m=Decimal("10.00"),
            ),
        },
        # OpenRouter uses dynamic pricing from their API
        # These are placeholder values for testing
        "openrouter": {
            "anthropic/claude-sonnet-4-5": ProviderPricing(
                provider="openrouter",
                model="anthropic/claude-sonnet-4-5",
                input_price_per_1m=Decimal("3.00"),
                output_price_per_1m=Decimal("15.00"),
            ),
            "openai/gpt-4o": ProviderPricing(
                provider="openrouter",
                model="openai/gpt-4o",
                input_price_per_1m=Decimal("2.50"),
                output_price_per_1m=Decimal("10.00"),
            ),
        },
    }


@pytest.fixture
def static_pricing_provider(test_pricing_data, default_pricing):
    """Create a static pricing provider with test data."""
    from modules.usage.pricing import StaticPricingProvider
    return StaticPricingProvider(test_pricing_data, default_pricing)


@pytest.fixture
def hybrid_pricing_provider(test_pricing_data, default_pricing):
    """Create a hybrid pricing provider with test data (no OpenRouter key)."""
    from modules.usage.pricing import HybridPricingProvider
    return HybridPricingProvider(
        openrouter_api_key=None,
        static_pricing_data=test_pricing_data,
        default_pricing=default_pricing,
    )


@pytest.fixture
def usage_service(test_pricing_data, default_pricing):
    """Create a usage service with test pricing data."""
    from modules.usage.service import UsageService
    from modules.usage.pricing import StaticPricingProvider
    
    pricing_provider = StaticPricingProvider(test_pricing_data, default_pricing)
    return UsageService(pricing_provider=pricing_provider)

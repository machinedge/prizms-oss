"""Tests for pricing providers."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import os

from modules.usage.pricing import (
    StaticPricingProvider,
    OpenRouterPricingProvider,
    HybridPricingProvider,
    get_pricing_provider,
    reset_pricing_provider,
    DEFAULT_FALLBACK_PRICING,
)
from modules.usage.models import ProviderPricing
from modules.usage.exceptions import PricingFetchError


class TestStaticPricingProvider:
    @pytest.mark.asyncio
    async def test_get_pricing_exact_match(self, static_pricing_provider):
        """Should return pricing for exact model match."""
        pricing = await static_pricing_provider.get_pricing("anthropic", "claude-sonnet-4-5")
        assert pricing.provider == "anthropic"
        assert pricing.model == "claude-sonnet-4-5"
        assert pricing.input_price_per_1m == Decimal("3.00")

    @pytest.mark.asyncio
    async def test_get_pricing_prefix_match(self, static_pricing_provider):
        """Should match model by prefix."""
        pricing = await static_pricing_provider.get_pricing("anthropic", "claude-sonnet-4-5-20250115")
        # Should match claude-sonnet-4-5
        assert pricing.provider == "anthropic"
        assert pricing.input_price_per_1m == Decimal("3.00")

    @pytest.mark.asyncio
    async def test_get_pricing_unknown_returns_default(self, static_pricing_provider, default_pricing):
        """Should return default pricing for unknown model."""
        pricing = await static_pricing_provider.get_pricing("unknown-provider", "unknown-model")
        assert pricing == default_pricing

    def test_get_pricing_sync(self, static_pricing_provider):
        """Should work synchronously."""
        pricing = static_pricing_provider.get_pricing_sync("openai", "gpt-4o")
        assert pricing.provider == "openai"
        assert pricing.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_refresh_cache_noop(self, static_pricing_provider):
        """Refresh cache should be no-op for static provider."""
        # Should not raise
        await static_pricing_provider.refresh_cache()

    def test_empty_provider_returns_default(self, default_pricing):
        """Provider with no data should return default pricing."""
        provider = StaticPricingProvider(pricing_data=None, default_pricing=default_pricing)
        pricing = provider.get_pricing_sync("any", "model")
        assert pricing == default_pricing

    def test_default_pricing_property(self, static_pricing_provider, default_pricing):
        """Should expose default pricing via property."""
        assert static_pricing_provider.default_pricing == default_pricing


class TestOpenRouterPricingProvider:
    @pytest.fixture
    def provider(self):
        """Create OpenRouter pricing provider without API key."""
        return OpenRouterPricingProvider(api_key=None)

    @pytest.fixture
    def provider_with_key(self):
        """Create OpenRouter pricing provider with API key."""
        return OpenRouterPricingProvider(api_key="test-api-key")

    def test_is_configured_without_key(self, provider):
        """Should not be configured without API key."""
        assert provider.is_configured is False

    def test_is_configured_with_key(self, provider_with_key):
        """Should be configured with API key."""
        assert provider_with_key.is_configured is True

    @pytest.mark.asyncio
    async def test_get_pricing_without_key_returns_fallback(self, provider):
        """Should return fallback pricing without API key."""
        pricing = await provider.get_pricing("anthropic", "claude-sonnet-4-5")
        # Returns fallback pricing since no API key
        assert pricing == DEFAULT_FALLBACK_PRICING

    @pytest.mark.asyncio
    async def test_fetch_models_without_key_raises(self, provider):
        """Should raise error when fetching without API key."""
        with pytest.raises(PricingFetchError) as exc_info:
            await provider._fetch_models()
        assert "API key not configured" in str(exc_info.value)

    def test_parse_model_pricing(self, provider):
        """Should parse OpenRouter model pricing correctly."""
        model_data = {
            "id": "anthropic/claude-3-opus",
            "pricing": {
                "prompt": "0.000015",  # $15/M tokens
                "completion": "0.000075",  # $75/M tokens
            }
        }

        pricing = provider._parse_model_pricing(model_data)

        assert pricing.provider == "anthropic"
        assert pricing.model == "anthropic/claude-3-opus"
        assert pricing.input_price_per_1m == Decimal("15.000000")
        assert pricing.output_price_per_1m == Decimal("75.000000")

    def test_parse_model_pricing_with_cache(self, provider):
        """Should parse cached pricing when available."""
        model_data = {
            "id": "anthropic/claude-3-sonnet",
            "pricing": {
                "prompt": "0.000003",
                "completion": "0.000015",
                "input_cache_read": "0.0000003",
            }
        }

        pricing = provider._parse_model_pricing(model_data)

        assert pricing.cached_input_price_per_1m == Decimal("0.300000")

    @pytest.mark.asyncio
    async def test_get_pricing_from_cache(self, provider_with_key):
        """Should return pricing from cache after refresh."""
        # Manually populate cache
        provider_with_key._cache = {
            "anthropic/claude-3-opus": ProviderPricing(
                provider="anthropic",
                model="anthropic/claude-3-opus",
                input_price_per_1m=Decimal("15.00"),
                output_price_per_1m=Decimal("75.00"),
            )
        }
        from datetime import datetime, timezone
        provider_with_key._cache_timestamp = datetime.now(timezone.utc)

        pricing = provider_with_key.get_pricing_sync("anthropic", "claude-3-opus")
        assert pricing.input_price_per_1m == Decimal("15.00")

    @pytest.mark.asyncio
    async def test_refresh_cache_success(self, provider_with_key):
        """Should refresh cache from API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "openai/gpt-4",
                    "pricing": {
                        "prompt": "0.00003",
                        "completion": "0.00006",
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            await provider_with_key.refresh_cache()

        assert len(provider_with_key._cache) == 1
        assert "openai/gpt-4" in provider_with_key._cache

    def test_default_pricing_property(self, provider):
        """Should expose default pricing via property."""
        assert provider.default_pricing == DEFAULT_FALLBACK_PRICING


class TestHybridPricingProvider:
    @pytest.mark.asyncio
    async def test_get_pricing_static_first(self, hybrid_pricing_provider):
        """Should try static pricing first for non-OpenRouter providers."""
        pricing = await hybrid_pricing_provider.get_pricing("anthropic", "claude-sonnet-4-5")
        assert pricing.provider == "anthropic"
        assert pricing.input_price_per_1m == Decimal("3.00")

    @pytest.mark.asyncio
    async def test_get_pricing_unknown_returns_default(self, hybrid_pricing_provider, default_pricing):
        """Should return default for unknown models."""
        pricing = await hybrid_pricing_provider.get_pricing("unknown", "unknown-model")
        assert pricing == default_pricing

    def test_get_pricing_sync(self, hybrid_pricing_provider):
        """Should work synchronously."""
        pricing = hybrid_pricing_provider.get_pricing_sync("google", "gemini-2.0-flash")
        assert pricing.provider == "google"

    @pytest.mark.asyncio
    async def test_refresh_cache_without_key(self, hybrid_pricing_provider):
        """Should not fail when refreshing without OpenRouter key."""
        # Should not raise
        await hybrid_pricing_provider.refresh_cache()

    def test_default_pricing_property(self, hybrid_pricing_provider, default_pricing):
        """Should expose default pricing via property."""
        assert hybrid_pricing_provider.default_pricing == default_pricing


class TestPricingProviderSingleton:
    def test_get_pricing_provider(self):
        """Should return singleton instance."""
        reset_pricing_provider()
        provider1 = get_pricing_provider()
        provider2 = get_pricing_provider()
        assert provider1 is provider2

    def test_reset_pricing_provider(self):
        """Should reset singleton."""
        reset_pricing_provider()
        provider1 = get_pricing_provider()
        reset_pricing_provider()
        provider2 = get_pricing_provider()
        assert provider1 is not provider2


class TestEnvironmentApiKey:
    def test_openrouter_key_from_env(self):
        """Should read API key from environment."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key"}):
            provider = OpenRouterPricingProvider()
            assert provider._api_key == "env-key"
            assert provider.is_configured is True

    def test_explicit_key_overrides_env(self):
        """Explicit key should override environment."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key"}):
            provider = OpenRouterPricingProvider(api_key="explicit-key")
            assert provider._api_key == "explicit-key"

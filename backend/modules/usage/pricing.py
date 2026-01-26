"""
Pricing providers for the usage module.

This module implements the IPricingProvider interface with multiple
implementations:
- StaticPricingProvider: Uses injected pricing data
- OpenRouterPricingProvider: Fetches pricing from OpenRouter API
- HybridPricingProvider: Tries OpenRouter first, falls back to static
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import os

from .interfaces import IPricingProvider
from .models import ProviderPricing
from .exceptions import UnknownModelError, PricingFetchError

logger = logging.getLogger(__name__)


# Sensible default for unknown models (conservative estimate)
DEFAULT_FALLBACK_PRICING = ProviderPricing(
    provider="unknown",
    model="unknown",
    input_price_per_1m=Decimal("5.00"),
    output_price_per_1m=Decimal("15.00"),
)


class StaticPricingProvider:
    """
    Pricing provider using injected pricing data.

    This provider accepts pricing data as a constructor parameter,
    allowing tests to inject test data and production to inject
    data loaded from Supabase or other sources.
    """

    def __init__(
        self,
        pricing_data: Optional[dict[str, dict[str, ProviderPricing]]] = None,
        default_pricing: Optional[ProviderPricing] = None,
    ):
        """
        Initialize the static pricing provider.

        Args:
            pricing_data: Dictionary of provider -> model -> ProviderPricing.
                         If None, no static pricing is available.
            default_pricing: Fallback pricing for unknown models.
                           If None, uses DEFAULT_FALLBACK_PRICING.
        """
        self._pricing = pricing_data or {}
        self._default = default_pricing or DEFAULT_FALLBACK_PRICING

    @property
    def default_pricing(self) -> ProviderPricing:
        """Get the default pricing used for unknown models."""
        return self._default

    async def get_pricing(self, provider: str, model: str) -> ProviderPricing:
        """Get pricing from static data."""
        return self.get_pricing_sync(provider, model)

    async def refresh_cache(self) -> None:
        """No-op for static provider - data is injected."""
        pass

    def get_pricing_sync(self, provider: str, model: str) -> ProviderPricing:
        """Get pricing synchronously from static data."""
        provider_models = self._pricing.get(provider, {})

        # Try exact match first
        if model in provider_models:
            return provider_models[model]

        # Try prefix match (e.g., "claude-sonnet-4-5" matches "claude-sonnet-4-5-20250115")
        for model_key, pricing in provider_models.items():
            if model_key.startswith(model) or model.startswith(model_key):
                return pricing

        # Return default pricing with warning
        logger.warning(
            f"No pricing found for {provider}/{model}, using default pricing"
        )
        return self._default


class OpenRouterPricingProvider:
    """
    Pricing provider that fetches from OpenRouter API.

    OpenRouter provides pricing for 400+ models across 60+ providers,
    making it an excellent source for dynamic pricing data.

    API Endpoint: https://openrouter.ai/api/v1/models
    Response includes pricing.prompt and pricing.completion per token.
    """

    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"
    CACHE_TTL_SECONDS = 3600  # 1 hour

    def __init__(
        self,
        api_key: Optional[str] = None,
        fallback_pricing: Optional[ProviderPricing] = None,
    ):
        """
        Initialize the OpenRouter pricing provider.

        Args:
            api_key: OpenRouter API key. If not provided, will try
                     OPENROUTER_API_KEY environment variable.
            fallback_pricing: Pricing to return for unknown models.
                            If None, uses DEFAULT_FALLBACK_PRICING.
        """
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self._cache: dict[str, ProviderPricing] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._fallback = fallback_pricing or DEFAULT_FALLBACK_PRICING

    @property
    def is_configured(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self._api_key)

    @property
    def default_pricing(self) -> ProviderPricing:
        """Get the default pricing used for unknown models."""
        return self._fallback

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_timestamp:
            return False
        age = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age < self.CACHE_TTL_SECONDS

    async def _fetch_models(self) -> list[dict]:
        """Fetch models from OpenRouter API."""
        if not self._api_key:
            raise PricingFetchError(
                "openrouter",
                "API key not configured"
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.OPENROUTER_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
        except ImportError:
            raise PricingFetchError(
                "openrouter",
                "httpx package not installed"
            )
        except Exception as e:
            raise PricingFetchError("openrouter", str(e))

    def _parse_model_pricing(self, model_data: dict) -> ProviderPricing:
        """Parse model pricing from OpenRouter response."""
        model_id = model_data.get("id", "unknown")
        pricing = model_data.get("pricing", {})

        # OpenRouter prices are per token, convert to per 1M tokens
        prompt_per_token = Decimal(str(pricing.get("prompt", "0")))
        completion_per_token = Decimal(str(pricing.get("completion", "0")))

        input_per_1m = prompt_per_token * 1_000_000
        output_per_1m = completion_per_token * 1_000_000

        # Handle cached pricing if available
        cached_per_1m = None
        if "input_cache_read" in pricing:
            cached_per_token = Decimal(str(pricing.get("input_cache_read", "0")))
            cached_per_1m = cached_per_token * 1_000_000

        # Extract provider from model ID (format: "provider/model")
        provider = "openrouter"
        if "/" in model_id:
            provider = model_id.split("/")[0]

        return ProviderPricing(
            provider=provider,
            model=model_id,
            input_price_per_1m=input_per_1m,
            output_price_per_1m=output_per_1m,
            cached_input_price_per_1m=cached_per_1m,
        )

    async def refresh_cache(self) -> None:
        """Fetch fresh pricing data from OpenRouter."""
        if not self.is_configured:
            # No API key configured, nothing to refresh
            logger.debug("OpenRouter API key not configured, skipping cache refresh")
            return

        try:
            models = await self._fetch_models()
            new_cache = {}

            for model_data in models:
                model_id = model_data.get("id")
                if model_id:
                    pricing = self._parse_model_pricing(model_data)
                    new_cache[model_id] = pricing

            self._cache = new_cache
            self._cache_timestamp = datetime.now(timezone.utc)
            logger.info(f"Refreshed OpenRouter pricing cache: {len(new_cache)} models")
        except PricingFetchError:
            # Log but don't raise - we'll fall back to default pricing
            logger.warning("Failed to refresh OpenRouter pricing cache")
            raise

    async def get_pricing(self, provider: str, model: str) -> ProviderPricing:
        """Get pricing from OpenRouter, refreshing cache if needed."""
        if not self.is_configured:
            # Fall back to default pricing if not configured
            logger.warning(
                f"OpenRouter not configured, using default pricing for {provider}/{model}"
            )
            return self._fallback

        # Refresh cache if expired
        if not self._is_cache_valid():
            try:
                await self.refresh_cache()
            except PricingFetchError:
                # Fall back to default on failure
                return self._fallback

        return self.get_pricing_sync(provider, model)

    def get_pricing_sync(self, provider: str, model: str) -> ProviderPricing:
        """Get pricing from cache synchronously."""
        # Try OpenRouter model ID format first
        if provider != "openrouter":
            openrouter_id = f"{provider}/{model}"
            if openrouter_id in self._cache:
                return self._cache[openrouter_id]

        # Try direct model ID
        if model in self._cache:
            return self._cache[model]

        # Try prefix matching
        for model_key, pricing in self._cache.items():
            if model in model_key or model_key.endswith(model):
                return pricing

        # Fall back to default pricing
        return self._fallback


class HybridPricingProvider:
    """
    Hybrid pricing provider that combines OpenRouter and static pricing.

    - Tries OpenRouter first if API key is configured
    - Falls back to static pricing on failure or if not configured
    - Provides seamless pricing resolution for all providers
    """

    def __init__(
        self,
        openrouter_api_key: Optional[str] = None,
        static_pricing_data: Optional[dict[str, dict[str, ProviderPricing]]] = None,
        default_pricing: Optional[ProviderPricing] = None,
    ):
        """
        Initialize the hybrid pricing provider.

        Args:
            openrouter_api_key: Optional OpenRouter API key. If not provided,
                               will try OPENROUTER_API_KEY environment variable.
            static_pricing_data: Optional static pricing data to use as fallback.
            default_pricing: Fallback pricing for unknown models.
        """
        self._default = default_pricing or DEFAULT_FALLBACK_PRICING
        self._openrouter = OpenRouterPricingProvider(
            openrouter_api_key,
            fallback_pricing=self._default,
        )
        self._static = StaticPricingProvider(
            static_pricing_data,
            default_pricing=self._default,
        )

    @property
    def default_pricing(self) -> ProviderPricing:
        """Get the default pricing used for unknown models."""
        return self._default

    async def get_pricing(self, provider: str, model: str) -> ProviderPricing:
        """
        Get pricing using hybrid resolution.

        For OpenRouter-routed models (provider="openrouter"), always try
        OpenRouter API first. For direct provider calls, try static first
        then OpenRouter as fallback.
        """
        if provider == "openrouter" and self._openrouter.is_configured:
            try:
                return await self._openrouter.get_pricing(provider, model)
            except (PricingFetchError, UnknownModelError):
                pass

        # Try static pricing first for non-OpenRouter providers
        try:
            pricing = await self._static.get_pricing(provider, model)
            if pricing != self._default:
                return pricing
        except UnknownModelError:
            pass

        # Try OpenRouter as fallback if configured
        if self._openrouter.is_configured:
            try:
                return await self._openrouter.get_pricing(provider, model)
            except (PricingFetchError, UnknownModelError):
                pass

        # Final fallback to default
        return self._default

    async def refresh_cache(self) -> None:
        """Refresh all pricing caches."""
        if self._openrouter.is_configured:
            try:
                await self._openrouter.refresh_cache()
            except PricingFetchError:
                logger.warning("Failed to refresh OpenRouter cache")

    def get_pricing_sync(self, provider: str, model: str) -> ProviderPricing:
        """Get pricing synchronously using cached data only."""
        # Try static first
        pricing = self._static.get_pricing_sync(provider, model)
        if pricing != self._default:
            return pricing

        # Try OpenRouter cache
        if self._openrouter.is_configured:
            pricing = self._openrouter.get_pricing_sync(provider, model)
            if pricing != self._default:
                return pricing

        return self._default


# Module-level instance getter
_pricing_provider: Optional[HybridPricingProvider] = None


def get_pricing_provider() -> HybridPricingProvider:
    """Get the default hybrid pricing provider singleton."""
    global _pricing_provider
    if _pricing_provider is None:
        _pricing_provider = HybridPricingProvider()
    return _pricing_provider


def reset_pricing_provider() -> None:
    """Reset the pricing provider singleton (for testing)."""
    global _pricing_provider
    _pricing_provider = None

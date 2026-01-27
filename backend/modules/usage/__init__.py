"""
Usage tracking module.

Handles token counting, cost calculation, and usage history.

Public API:
- IUsageService: Interface for usage operations
- IPricingProvider: Interface for pricing providers
- UsageRecord: Single usage record
- CostEstimate: Cost estimation result
- UsageSummary: Aggregated usage data
- ProviderPricing: Provider pricing information
"""

from .interfaces import IUsageService, IPricingProvider
from .models import (
    UsageRecord,
    CostEstimate,
    UsageSummary,
    ProviderPricing,
)
from .exceptions import (
    UsageError,
    UnknownProviderError,
    UnknownModelError,
    InvalidTokenCountError,
    PricingFetchError,
)
from .pricing import (
    StaticPricingProvider,
    OpenRouterPricingProvider,
    HybridPricingProvider,
    get_pricing_provider,
)
from .service import (
    UsageService,
    SupabaseUsageService,
    get_usage_service,
    reset_usage_service,
)
from .token_counter import (
    count_tokens,
    count_message_tokens,
    estimate_output_tokens,
)

__all__ = [
    # Interfaces
    "IUsageService",
    "IPricingProvider",
    # Models
    "UsageRecord",
    "CostEstimate",
    "UsageSummary",
    "ProviderPricing",
    # Exceptions
    "UsageError",
    "UnknownProviderError",
    "UnknownModelError",
    "InvalidTokenCountError",
    "PricingFetchError",
    # Pricing Providers
    "StaticPricingProvider",
    "OpenRouterPricingProvider",
    "HybridPricingProvider",
    "get_pricing_provider",
    # Service
    "UsageService",
    "SupabaseUsageService",
    "get_usage_service",
    "reset_usage_service",
    # Token counting
    "count_tokens",
    "count_message_tokens",
    "estimate_output_tokens",
]

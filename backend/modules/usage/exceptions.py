"""
Usage tracking module exceptions.
"""

from shared.exceptions import PrizmsError, ValidationError


class UsageError(PrizmsError):
    """Base exception for usage-related errors."""

    pass


class UnknownProviderError(UsageError):
    """Raised when an unknown provider is specified."""

    def __init__(self, provider: str):
        super().__init__(
            f"Unknown provider: {provider}",
            code="UNKNOWN_PROVIDER",
            details={"provider": provider},
        )


class UnknownModelError(UsageError):
    """Raised when an unknown model is specified."""

    def __init__(self, provider: str, model: str):
        super().__init__(
            f"Unknown model: {model} for provider {provider}",
            code="UNKNOWN_MODEL",
            details={"provider": provider, "model": model},
        )


class InvalidTokenCountError(ValidationError):
    """Raised when token counts are invalid."""

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_TOKEN_COUNT")


class PricingFetchError(UsageError):
    """Raised when fetching pricing from an external API fails."""

    def __init__(self, provider: str, message: str):
        super().__init__(
            f"Failed to fetch pricing from {provider}: {message}",
            code="PRICING_FETCH_ERROR",
            details={"provider": provider, "error": message},
        )

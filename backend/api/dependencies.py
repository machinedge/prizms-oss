"""
Dependency injection setup for FastAPI.

This module provides the "container" that wires together all module
implementations. Each module exposes its service through an interface,
and this file creates the concrete implementations.

When we're ready to extract a module to a microservice, we only need
to change the implementation here to an HTTP client.
"""

from typing import TYPE_CHECKING

# Type checking imports for interfaces (avoids circular imports)
if TYPE_CHECKING:
    from modules.auth.interfaces import IAuthService
    from modules.billing.interfaces import IBillingService
    from modules.usage.interfaces import IUsageService
    from modules.debates.interfaces import IDebateService
    from modules.debates.repository import DebateRepository


class ServiceContainer:
    """
    Container for all service instances.

    This class manages the lifecycle of service instances and their
    dependencies. Services are created lazily on first access.

    All services are cached as singletons within the container.
    Use reset() to clear all cached services for testing.
    """

    def __init__(self) -> None:
        self._auth_service: "IAuthService | None" = None
        self._billing_service: "IBillingService | None" = None
        self._usage_service: "IUsageService | None" = None
        self._debate_service: "IDebateService | None" = None
        self._debate_repository: "DebateRepository | None" = None

    @property
    def auth(self) -> "IAuthService":
        """Get the auth service instance."""
        if self._auth_service is None:
            from modules.auth.service import AuthService
            self._auth_service = AuthService()
        return self._auth_service

    @property
    def billing(self) -> "IBillingService":
        """Get the billing service instance."""
        if self._billing_service is None:
            from modules.billing.service import BillingService
            self._billing_service = BillingService()
        return self._billing_service

    @property
    def usage(self) -> "IUsageService":
        """Get the usage service instance."""
        if self._usage_service is None:
            from modules.usage.service import UsageService
            self._usage_service = UsageService()
        return self._usage_service

    @property
    def debate_repository(self) -> "DebateRepository":
        """Get the debate repository instance."""
        if self._debate_repository is None:
            from modules.debates.repository import DebateRepository
            from shared.database import get_supabase_client
            self._debate_repository = DebateRepository(get_supabase_client())
        return self._debate_repository

    @property
    def debates(self) -> "IDebateService":
        """Get the debate service instance."""
        if self._debate_service is None:
            from modules.debates.service import DebateService
            self._debate_service = DebateService(
                repository=self.debate_repository,
                auth=None,   # Will be wired in future stories
                usage=None,  # Will be wired in future stories
            )
        return self._debate_service

    def reset(self) -> None:
        """
        Reset all cached services.

        This is primarily for testing - allows tests to get fresh
        service instances with different mock dependencies.
        """
        self._auth_service = None
        self._billing_service = None
        self._usage_service = None
        self._debate_service = None
        self._debate_repository = None


# Module-level container singleton
_container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    """Get the singleton service container."""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def reset_container() -> None:
    """
    Reset the service container.

    This clears the cached container, so the next call to get_container()
    will create a fresh container with new service instances.

    Primarily used for testing.
    """
    global _container
    _container = None


# FastAPI dependency functions
# These are the functions that should be used in route Depends() calls


def get_auth_service() -> "IAuthService":
    """FastAPI dependency for auth service."""
    return get_container().auth


def get_billing_service() -> "IBillingService":
    """FastAPI dependency for billing service."""
    return get_container().billing


def get_usage_service() -> "IUsageService":
    """FastAPI dependency for usage service."""
    return get_container().usage


def get_debate_service() -> "IDebateService":
    """FastAPI dependency for debate service."""
    return get_container().debates


def get_debate_repository() -> "DebateRepository":
    """FastAPI dependency for debate repository."""
    return get_container().debate_repository

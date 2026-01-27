"""
Dependency injection setup for FastAPI.

This module provides the "container" that wires together all module
implementations. Each module exposes its service through an interface,
and this file creates the concrete implementations.

When we're ready to extract a module to a microservice, we only need
to change the implementation here to an HTTP client.
"""

from functools import lru_cache
from typing import TYPE_CHECKING, Any

# Type checking imports for interfaces (avoids circular imports)
if TYPE_CHECKING:
    pass
    # TODO: Uncomment when interfaces are defined in Stories 07-10
    # from modules.auth.interfaces import IAuthService
    # from modules.billing.interfaces import IBillingService
    # from modules.usage.interfaces import IUsageService
    # from modules.debates.interfaces import IDebateService


class ServiceContainer:
    """
    Container for all service instances.

    This class manages the lifecycle of service instances and their
    dependencies. Services are created lazily on first access.
    """

    def __init__(self) -> None:
        self._auth_service: Any = None
        self._billing_service: Any = None
        self._usage_service: Any = None
        self._debate_service: Any = None

    @property
    def auth(self) -> Any:  # TODO: Return type should be "IAuthService"
        """Get the auth service instance."""
        if self._auth_service is None:
            # TODO: Implement in Story 12
            # from modules.auth.service import AuthService
            # self._auth_service = AuthService()
            raise NotImplementedError(
                "AuthService not yet implemented. See Story 12."
            )
        return self._auth_service

    @property
    def billing(self) -> Any:  # TODO: Return type should be "IBillingService"
        """Get the billing service instance."""
        if self._billing_service is None:
            # TODO: Implement in Story 16
            # from modules.billing.service import BillingService
            # self._billing_service = BillingService()
            raise NotImplementedError(
                "BillingService not yet implemented. See Story 16."
            )
        return self._billing_service

    @property
    def usage(self) -> Any:  # TODO: Return type should be "IUsageService"
        """Get the usage service instance."""
        if self._usage_service is None:
            # TODO: Implement in Story 15
            # from modules.usage.service import UsageService
            # self._usage_service = UsageService()
            raise NotImplementedError(
                "UsageService not yet implemented. See Story 15."
            )
        return self._usage_service

    @property
    def debates(self) -> Any:  # TODO: Return type should be "IDebateService"
        """Get the debate service instance."""
        if self._debate_service is None:
            from modules.debates.repository import DebateRepository
            from modules.debates.service import DebateService
            from shared.database import get_supabase_client

            repository = DebateRepository(get_supabase_client())
            self._debate_service = DebateService(
                repository=repository,
                auth=None,   # Will be wired in future stories
                usage=None,  # Will be wired in future stories
            )
        return self._debate_service


@lru_cache
def get_container() -> ServiceContainer:
    """Get the singleton service container."""
    return ServiceContainer()


# FastAPI dependency functions
def get_auth_service() -> Any:  # TODO: Return type should be "IAuthService"
    """FastAPI dependency for auth service."""
    return get_container().auth


def get_billing_service() -> Any:  # TODO: Return type should be "IBillingService"
    """FastAPI dependency for billing service."""
    return get_container().billing


def get_usage_service() -> Any:  # TODO: Return type should be "IUsageService"
    """FastAPI dependency for usage service."""
    return get_container().usage


def get_debate_service() -> Any:  # TODO: Return type should be "IDebateService"
    """FastAPI dependency for debate service."""
    return get_container().debates

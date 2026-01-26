"""
Debates module exceptions.
"""

from typing import Optional

from shared.exceptions import (
    PrizmsError,
    NotFoundError,
    ValidationError,
    AuthorizationError,
)


class DebateError(PrizmsError):
    """Base exception for debate-related errors."""

    pass


class DebateNotFoundError(NotFoundError):
    """Raised when a debate is not found."""

    def __init__(self, debate_id: str):
        super().__init__(
            f"Debate not found: {debate_id}",
            code="DEBATE_NOT_FOUND",
            details={"debate_id": debate_id},
        )


class DebateAccessDeniedError(AuthorizationError):
    """Raised when user doesn't have access to a debate."""

    def __init__(self, debate_id: str, user_id: str):
        super().__init__(
            f"Access denied to debate: {debate_id}",
            code="DEBATE_ACCESS_DENIED",
            details={"debate_id": debate_id, "user_id": user_id},
        )


class DebateAlreadyActiveError(ValidationError):
    """Raised when trying to start an already active debate."""

    def __init__(self, debate_id: str):
        super().__init__(
            f"Debate is already active: {debate_id}",
            code="DEBATE_ALREADY_ACTIVE",
            details={"debate_id": debate_id},
        )


class DebateAlreadyCompletedError(ValidationError):
    """Raised when trying to modify a completed debate."""

    def __init__(self, debate_id: str):
        super().__init__(
            f"Debate is already completed: {debate_id}",
            code="DEBATE_ALREADY_COMPLETED",
            details={"debate_id": debate_id},
        )


class DebateCancelledError(DebateError):
    """Raised when a debate is cancelled during execution."""

    def __init__(self, debate_id: str):
        super().__init__(
            f"Debate was cancelled: {debate_id}",
            code="DEBATE_CANCELLED",
            details={"debate_id": debate_id},
        )


class ProviderError(DebateError):
    """Raised when an LLM provider returns an error."""

    def __init__(
        self,
        provider: str,
        message: str,
        original_error: Optional[str] = None,
    ):
        super().__init__(
            f"Provider error ({provider}): {message}",
            code="PROVIDER_ERROR",
            details={
                "provider": provider,
                "original_error": original_error,
            },
        )

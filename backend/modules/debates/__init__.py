"""
Debates module.

Handles debate creation, orchestration, and streaming.

Public API:
- IDebateService: Interface for debate operations
- Debate: Full debate with all data
- DebateEvent: SSE event for streaming
- CreateDebateRequest: Request to create a debate
"""

from .interfaces import IDebateService
from .models import (
    Debate,
    DebateListItem,
    DebateListResponse,
    DebateRound,
    DebateSynthesis,
    PersonalityResponse,
    CreateDebateRequest,
    DebateSettings,
    DebateStatus,
    DebateEvent,
    DebateEventType,
    SYSTEM_PERSONALITIES,
    get_default_personalities,
)
from .exceptions import (
    DebateError,
    DebateNotFoundError,
    DebateAccessDeniedError,
    DebateAlreadyActiveError,
    DebateAlreadyCompletedError,
    DebateCancelledError,
    ProviderError,
)

__all__ = [
    # Interface
    "IDebateService",
    # Models
    "Debate",
    "DebateListItem",
    "DebateListResponse",
    "DebateRound",
    "DebateSynthesis",
    "PersonalityResponse",
    "CreateDebateRequest",
    "DebateSettings",
    "DebateStatus",
    "DebateEvent",
    "DebateEventType",
    "SYSTEM_PERSONALITIES",
    "get_default_personalities",
    # Exceptions
    "DebateError",
    "DebateNotFoundError",
    "DebateAccessDeniedError",
    "DebateAlreadyActiveError",
    "DebateAlreadyCompletedError",
    "DebateCancelledError",
    "ProviderError",
]

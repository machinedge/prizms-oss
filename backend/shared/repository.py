"""
Base repository class for database access.

Provides a common abstraction layer for all repositories, encapsulating
Supabase client access and providing shared utilities for data operations.
"""

from typing import TypeVar, Generic
from supabase import Client


T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base class for all repositories.

    Provides common functionality for database operations:
    - Supabase client access via self._db
    - Generic type parameter for model type hints

    Subclasses should implement domain-specific data access methods
    and handle dict-to-Pydantic model mapping internally.

    Example:
        class DebateRepository(BaseRepository[Debate]):
            def get_by_id(self, debate_id: str) -> Optional[Debate]:
                result = self._db.table("debates").select("*").eq("id", debate_id).execute()
                if not result.data:
                    return None
                return self._map_to_debate(result.data[0])
    """

    def __init__(self, db: Client) -> None:
        """
        Initialize the repository with a Supabase client.

        Args:
            db: Supabase client instance for database operations.
        """
        self._db = db

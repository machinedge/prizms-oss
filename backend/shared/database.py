"""
Database client factory for Supabase.

Provides both service-role clients (for backend operations bypassing RLS)
and user-authenticated clients (for operations respecting RLS).
"""

from typing import Optional
from supabase import create_client, Client

from .config import get_settings

# Module-level client cache
_service_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get Supabase client with service role (bypasses RLS).

    Use this for backend operations that need full database access,
    such as inserting records on behalf of users during debates.

    Returns:
        Supabase client configured with service role key
    """
    global _service_client

    if _service_client is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "Supabase configuration missing. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables."
            )
        _service_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )

    return _service_client


def get_supabase_user_client(access_token: str) -> Client:
    """
    Get Supabase client authenticated as a specific user.

    Use this for operations that should respect Row Level Security (RLS),
    such as querying data that belongs to the authenticated user.

    Args:
        access_token: JWT access token from Supabase Auth

    Returns:
        Supabase client configured with user's access token
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError(
            "Supabase configuration missing. "
            "Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
        )

    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )
    # Set the session with the access token (refresh_token can be empty for backend use)
    client.auth.set_session(access_token, "")
    return client


def reset_client_cache() -> None:
    """
    Reset the cached database client.

    Useful for testing or when configuration changes.
    """
    global _service_client
    _service_client = None

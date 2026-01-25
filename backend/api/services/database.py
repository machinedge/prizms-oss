"""
Database service for Supabase operations.

Uses the service role key for backend operations that bypass RLS.
"""

from typing import Optional
from supabase import create_client, Client
from ..config import get_settings

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client with service role.

    Uses service role for backend operations that need
    to bypass RLS (e.g., inserting debate rounds).
    """
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client


def get_supabase_user_client(access_token: str) -> Client:
    """
    Get Supabase client authenticated as a specific user.

    Used for operations that should respect RLS.
    """
    settings = get_settings()
    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )
    client.auth.set_session(access_token, "")
    return client

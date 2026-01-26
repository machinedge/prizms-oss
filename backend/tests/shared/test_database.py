"""Tests for shared/database.py."""

import os

import pytest
from unittest.mock import patch, MagicMock

from shared.database import (
    get_supabase_client,
    get_supabase_user_client,
    reset_client_cache,
)


# Environment variables for integration tests
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


class TestSupabaseClient:
    def setup_method(self):
        """Reset cache before each test."""
        reset_client_cache()

    @patch("shared.database.create_client")
    @patch("shared.database.get_settings")
    def test_get_supabase_client_creates_client(self, mock_settings, mock_create):
        """Should create client with service role key."""
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_role_key = "test-key"
        mock_create.return_value = MagicMock()

        client = get_supabase_client()

        mock_create.assert_called_once_with(
            "https://test.supabase.co",
            "test-key",
        )
        assert client is not None

    @patch("shared.database.create_client")
    @patch("shared.database.get_settings")
    def test_get_supabase_client_caches_client(self, mock_settings, mock_create):
        """Should cache the client and not recreate it."""
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_role_key = "test-key"
        mock_create.return_value = MagicMock()

        client1 = get_supabase_client()
        client2 = get_supabase_client()

        # Should only be called once due to caching
        mock_create.assert_called_once()
        assert client1 is client2

    @patch("shared.database.get_settings")
    def test_get_supabase_client_raises_without_config(self, mock_settings):
        """Should raise if configuration is missing."""
        mock_settings.return_value.supabase_url = ""
        mock_settings.return_value.supabase_service_role_key = ""

        with pytest.raises(RuntimeError, match="configuration missing"):
            get_supabase_client()

    @patch("shared.database.get_settings")
    def test_get_supabase_client_raises_without_url(self, mock_settings):
        """Should raise if URL is missing."""
        mock_settings.return_value.supabase_url = ""
        mock_settings.return_value.supabase_service_role_key = "test-key"

        with pytest.raises(RuntimeError, match="configuration missing"):
            get_supabase_client()

    @patch("shared.database.get_settings")
    def test_get_supabase_client_raises_without_key(self, mock_settings):
        """Should raise if service role key is missing."""
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_role_key = ""

        with pytest.raises(RuntimeError, match="configuration missing"):
            get_supabase_client()


class TestSupabaseUserClient:
    def setup_method(self):
        """Reset cache before each test."""
        reset_client_cache()

    @patch("shared.database.create_client")
    @patch("shared.database.get_settings")
    def test_get_supabase_user_client_creates_client(self, mock_settings, mock_create):
        """Should create client with anon key and set session."""
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_anon_key = "test-anon-key"
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        client = get_supabase_user_client("user-access-token")

        mock_create.assert_called_once_with(
            "https://test.supabase.co",
            "test-anon-key",
        )
        mock_client.auth.set_session.assert_called_once_with("user-access-token", "")
        assert client is mock_client

    @patch("shared.database.get_settings")
    def test_get_supabase_user_client_raises_without_config(self, mock_settings):
        """Should raise if configuration is missing."""
        mock_settings.return_value.supabase_url = ""
        mock_settings.return_value.supabase_anon_key = ""

        with pytest.raises(RuntimeError, match="configuration missing"):
            get_supabase_user_client("token")


class TestResetClientCache:
    def setup_method(self):
        """Reset cache before each test."""
        reset_client_cache()

    @patch("shared.database.create_client")
    @patch("shared.database.get_settings")
    def test_reset_client_cache(self, mock_settings, mock_create):
        """Should reset the cache and allow new client creation."""
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_role_key = "test-key"
        # Create new MagicMock for each call to verify different instances
        mock_create.side_effect = [MagicMock(name="client1"), MagicMock(name="client2")]

        # Create initial client
        client1 = get_supabase_client()
        assert mock_create.call_count == 1

        # Reset cache
        reset_client_cache()

        # Create new client - should call create_client again
        client2 = get_supabase_client()
        assert mock_create.call_count == 2
        assert client1 is not client2


# =============================================================================
# Integration Tests - Require real Supabase credentials
# =============================================================================


@pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY,
    reason="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables not set"
)
class TestSupabaseIntegration:
    """Integration tests requiring real Supabase credentials.

    These tests are skipped by default. To run them:
        SUPABASE_URL=https://xxx.supabase.co SUPABASE_SERVICE_ROLE_KEY=xxx \
            uv run pytest tests/shared/test_database.py -v -k Integration
    """

    def setup_method(self):
        """Reset cache before each test."""
        reset_client_cache()

    def test_service_client_connection(self):
        """Verify we can create a service client and query the database."""
        # Clear any cached settings
        from shared.config import get_settings
        get_settings.cache_clear()

        client = get_supabase_client()

        # The client should be created successfully
        assert client is not None

        # Try a simple RPC call or table query to verify connection
        # We'll use a query that should work on any Supabase project
        # by querying the auth.users table (which always exists)
        # Note: This requires service role key which bypasses RLS
        try:
            # Try to access auth schema to verify service role access
            # This is a lightweight check that doesn't require any specific tables
            response = client.auth.admin.list_users()
            # If we get here without exception, the connection works
            assert response is not None
        except Exception as e:
            # If there's an auth error, the client connected but may have permission issues
            # This is still a successful connection test
            if "unauthorized" in str(e).lower() or "forbidden" in str(e).lower():
                pytest.fail(f"Service role key doesn't have admin access: {e}")
            raise

    def test_client_caching_with_real_connection(self):
        """Verify client caching works with real credentials."""
        from shared.config import get_settings
        get_settings.cache_clear()

        client1 = get_supabase_client()
        client2 = get_supabase_client()

        # Should return the same cached instance
        assert client1 is client2

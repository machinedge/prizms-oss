"""Tests for debates module interfaces."""

import pytest
from unittest.mock import MagicMock

from modules.debates.interfaces import IDebateService
from modules.debates.service import DebateService
from modules.debates.repository import DebateRepository


class TestIDebateService:
    @pytest.fixture
    def mock_repository(self):
        """Create a mock DebateRepository."""
        return MagicMock(spec=DebateRepository)

    def test_protocol_is_runtime_checkable(self, mock_repository):
        """Should be able to check if instance implements protocol."""
        service = DebateService(repository=mock_repository)
        assert isinstance(service, IDebateService)

    def test_debate_service_implements_interface(self, mock_repository):
        """DebateService should implement all interface methods."""
        service = DebateService(repository=mock_repository)

        # Check all required methods exist
        assert hasattr(service, "create_debate")
        assert hasattr(service, "get_debate")
        assert hasattr(service, "list_debates")
        assert hasattr(service, "start_debate_stream")
        assert hasattr(service, "cancel_debate")
        assert hasattr(service, "delete_debate")

        # Check methods are callable
        assert callable(service.create_debate)
        assert callable(service.get_debate)
        assert callable(service.list_debates)
        assert callable(service.start_debate_stream)
        assert callable(service.cancel_debate)
        assert callable(service.delete_debate)

    def test_interface_with_dependencies(self, mock_repository):
        """Should accept optional dependencies."""
        # Mock dependencies
        mock_auth = object()
        mock_usage = object()

        service = DebateService(
            repository=mock_repository,
            auth=mock_auth,
            usage=mock_usage,
        )

        assert service._auth is mock_auth
        assert service._usage is mock_usage
        assert isinstance(service, IDebateService)

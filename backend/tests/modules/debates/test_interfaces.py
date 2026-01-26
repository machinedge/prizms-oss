"""Tests for debates module interfaces."""

import pytest

from modules.debates.interfaces import IDebateService
from modules.debates.service import DebateService


class TestIDebateService:
    def test_protocol_is_runtime_checkable(self):
        """Should be able to check if instance implements protocol."""
        service = DebateService()
        assert isinstance(service, IDebateService)

    def test_debate_service_implements_interface(self):
        """DebateService should implement all interface methods."""
        service = DebateService()

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

    def test_interface_with_dependencies(self):
        """Should accept optional dependencies."""
        # Mock dependencies
        mock_auth = object()
        mock_billing = object()
        mock_usage = object()

        service = DebateService(
            auth=mock_auth,
            billing=mock_billing,
            usage=mock_usage,
        )

        assert service._auth is mock_auth
        assert service._billing is mock_billing
        assert service._usage is mock_usage
        assert isinstance(service, IDebateService)

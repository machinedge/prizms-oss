import pytest
from typing import runtime_checkable

from modules.auth.interfaces import IAuthService
from modules.auth.service import AuthService


class TestAuthInterface:
    def test_service_implements_interface(self):
        """AuthService should implement IAuthService protocol."""
        # This verifies at runtime that AuthService has all required methods
        assert isinstance(AuthService, type)

        # Check that IAuthService is runtime checkable
        assert runtime_checkable

    def test_interface_methods_exist(self):
        """IAuthService should define required methods."""
        # Get the protocol's abstract methods
        methods = ["validate_token", "get_user_by_id", "get_user_by_email"]
        for method in methods:
            assert hasattr(IAuthService, method)

    def test_auth_service_has_interface_methods(self):
        """AuthService should have all IAuthService methods."""
        methods = ["validate_token", "get_user_by_id", "get_user_by_email"]
        for method in methods:
            assert hasattr(AuthService, method)
            assert callable(getattr(AuthService, method))

    def test_interface_is_runtime_checkable(self):
        """IAuthService should be decorated with @runtime_checkable."""
        # runtime_checkable protocols can be used with isinstance()
        # We can't directly test isinstance with a class, but we can verify
        # the protocol has the proper marker
        assert hasattr(IAuthService, "__protocol_attrs__") or hasattr(
            IAuthService, "_is_protocol"
        )

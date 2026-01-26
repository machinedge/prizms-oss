"""Tests for billing module interfaces."""

import pytest
from decimal import Decimal

from modules.billing.interfaces import IBillingService
from modules.billing.service import BillingService


class TestIBillingService:
    def test_protocol_is_runtime_checkable(self):
        """Should be able to check if instance implements protocol."""
        service = BillingService()
        assert isinstance(service, IBillingService)

    def test_billing_service_implements_interface(self):
        """BillingService should implement all interface methods."""
        service = BillingService()

        # Check all required methods exist
        assert hasattr(service, "get_balance")
        assert hasattr(service, "check_sufficient_credits")
        assert hasattr(service, "deduct_credits")
        assert hasattr(service, "add_credits")
        assert hasattr(service, "get_transaction_history")
        assert hasattr(service, "estimate_cost")

        # Check methods are callable
        assert callable(service.get_balance)
        assert callable(service.check_sufficient_credits)
        assert callable(service.deduct_credits)
        assert callable(service.add_credits)
        assert callable(service.get_transaction_history)
        assert callable(service.estimate_cost)

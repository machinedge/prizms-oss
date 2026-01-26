"""Tests for billing module models."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from modules.billing.models import (
    CreditBalance,
    Transaction,
    TransactionType,
    SubscriptionTier,
    CreditPack,
    DEFAULT_CREDIT_PACKS,
)


class TestTransactionType:
    def test_transaction_types_exist(self):
        """Should have all expected transaction types."""
        assert TransactionType.PURCHASE == "purchase"
        assert TransactionType.USAGE == "usage"
        assert TransactionType.FREE_TIER == "free_tier"
        assert TransactionType.REFUND == "refund"
        assert TransactionType.ADJUSTMENT == "adjustment"


class TestSubscriptionTier:
    def test_subscription_tiers_exist(self):
        """Should have all expected subscription tiers."""
        assert SubscriptionTier.FREE == "free"
        assert SubscriptionTier.PRO == "pro"
        assert SubscriptionTier.ENTERPRISE == "enterprise"


class TestCreditBalance:
    def test_create_balance(self):
        """Should create a credit balance."""
        balance = CreditBalance(
            user_id="user-123",
            balance=Decimal("25.50"),
            tier=SubscriptionTier.FREE,
        )
        assert balance.balance == Decimal("25.50")
        assert balance.tier == SubscriptionTier.FREE

    def test_default_tier(self):
        """Should default to free tier."""
        balance = CreditBalance(
            user_id="user-123",
            balance=Decimal("5.00"),
        )
        assert balance.tier == SubscriptionTier.FREE

    def test_default_monthly_allowance(self):
        """Should default to $5 monthly allowance."""
        balance = CreditBalance(
            user_id="user-123",
            balance=Decimal("10.00"),
        )
        assert balance.monthly_allowance == Decimal("5.00")
        assert balance.allowance_remaining == Decimal("5.00")

    def test_optional_allowance_reset(self):
        """Allowance reset time should be optional."""
        balance = CreditBalance(
            user_id="user-123",
            balance=Decimal("5.00"),
        )
        assert balance.allowance_resets_at is None

    def test_serialize_to_dict(self):
        """Should serialize Decimal to dict correctly."""
        balance = CreditBalance(
            user_id="user-123",
            balance=Decimal("25.50"),
        )
        data = balance.model_dump()
        assert data["balance"] == Decimal("25.50")
        assert data["user_id"] == "user-123"


class TestTransaction:
    def test_create_transaction(self):
        """Should create a transaction."""
        tx = Transaction(
            id="tx-123",
            user_id="user-123",
            amount=Decimal("-5.00"),
            type=TransactionType.USAGE,
            reason="Debate: What is AI?",
            balance_before=Decimal("25.00"),
            balance_after=Decimal("20.00"),
            created_at=datetime.now(timezone.utc),
        )
        assert tx.amount == Decimal("-5.00")
        assert tx.type == TransactionType.USAGE

    def test_optional_reference_id(self):
        """Reference ID should be optional."""
        tx = Transaction(
            id="tx-123",
            user_id="user-123",
            amount=Decimal("20.00"),
            type=TransactionType.PURCHASE,
            reason="Credit purchase",
            balance_before=Decimal("5.00"),
            balance_after=Decimal("25.00"),
            created_at=datetime.now(timezone.utc),
        )
        assert tx.reference_id is None

    def test_transaction_with_reference(self):
        """Should accept reference ID."""
        tx = Transaction(
            id="tx-123",
            user_id="user-123",
            amount=Decimal("-3.00"),
            type=TransactionType.USAGE,
            reason="Debate usage",
            reference_id="debate-456",
            balance_before=Decimal("10.00"),
            balance_after=Decimal("7.00"),
            created_at=datetime.now(timezone.utc),
        )
        assert tx.reference_id == "debate-456"


class TestCreditPack:
    def test_create_credit_pack(self):
        """Should create a credit pack."""
        pack = CreditPack(
            id="pack_test",
            name="Test Pack",
            amount=Decimal("10.00"),
            price=Decimal("10.00"),
        )
        assert pack.amount == Decimal("10.00")
        assert pack.price == Decimal("10.00")
        assert pack.popular is False

    def test_popular_pack(self):
        """Should mark popular packs."""
        pack = CreditPack(
            id="pack_popular",
            name="Popular Pack",
            amount=Decimal("20.00"),
            price=Decimal("20.00"),
            popular=True,
        )
        assert pack.popular is True


class TestDefaultCreditPacks:
    def test_default_packs_exist(self):
        """Should have default credit packs defined."""
        assert len(DEFAULT_CREDIT_PACKS) == 3

    def test_starter_pack(self):
        """Should have starter pack at $20."""
        starter = DEFAULT_CREDIT_PACKS[0]
        assert starter.id == "pack_20"
        assert starter.price == Decimal("20.00")
        assert starter.amount == Decimal("20.00")
        assert starter.popular is True

    def test_value_pack_bonus(self):
        """Value pack should have 10% bonus."""
        value = DEFAULT_CREDIT_PACKS[1]
        assert value.id == "pack_50"
        assert value.price == Decimal("50.00")
        assert value.amount == Decimal("55.00")  # 10% bonus

    def test_power_pack_bonus(self):
        """Power pack should have 20% bonus."""
        power = DEFAULT_CREDIT_PACKS[2]
        assert power.id == "pack_100"
        assert power.price == Decimal("100.00")
        assert power.amount == Decimal("120.00")  # 20% bonus

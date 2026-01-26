"""Tests for billing service."""

import pytest
from decimal import Decimal

from modules.billing.service import BillingService, get_billing_service
from modules.billing.models import TransactionType, SubscriptionTier
from modules.billing.exceptions import InsufficientCreditsError, InvalidAmountError


class TestBillingService:
    @pytest.fixture
    def service(self):
        """Create a fresh billing service for each test."""
        return BillingService()

    @pytest.mark.asyncio
    async def test_get_balance_default(self, service):
        """New users should have $5 free tier balance."""
        balance = await service.get_balance("new-user")
        assert balance.balance == Decimal("5.00")
        assert balance.tier == SubscriptionTier.FREE

    @pytest.mark.asyncio
    async def test_get_balance_returns_credit_balance(self, service):
        """Should return a CreditBalance with all fields."""
        balance = await service.get_balance("user-123")
        assert balance.user_id == "user-123"
        assert balance.monthly_allowance == Decimal("5.00")
        assert balance.allowance_remaining == Decimal("5.00")

    @pytest.mark.asyncio
    async def test_add_credits(self, service):
        """Should add credits to balance."""
        tx = await service.add_credits(
            user_id="user-123",
            amount=Decimal("20.00"),
            reason="Credit purchase",
        )
        assert tx.amount == Decimal("20.00")
        assert tx.type == TransactionType.PURCHASE

        balance = await service.get_balance("user-123")
        assert balance.balance == Decimal("25.00")  # 5 + 20

    @pytest.mark.asyncio
    async def test_add_credits_custom_type(self, service):
        """Should respect custom transaction type."""
        tx = await service.add_credits(
            user_id="user-123",
            amount=Decimal("5.00"),
            reason="Monthly free credits",
            transaction_type=TransactionType.FREE_TIER,
        )
        assert tx.type == TransactionType.FREE_TIER

    @pytest.mark.asyncio
    async def test_add_credits_with_stripe_id(self, service):
        """Should store stripe payment ID as reference."""
        tx = await service.add_credits(
            user_id="user-123",
            amount=Decimal("20.00"),
            reason="Credit purchase",
            stripe_payment_id="pi_123456789",
        )
        assert tx.reference_id == "pi_123456789"

    @pytest.mark.asyncio
    async def test_add_credits_invalid_amount(self, service):
        """Should reject zero or negative amounts."""
        with pytest.raises(InvalidAmountError):
            await service.add_credits(
                user_id="user-123",
                amount=Decimal("0"),
                reason="Invalid",
            )

        with pytest.raises(InvalidAmountError):
            await service.add_credits(
                user_id="user-123",
                amount=Decimal("-5.00"),
                reason="Invalid",
            )

    @pytest.mark.asyncio
    async def test_deduct_credits(self, service):
        """Should deduct credits from balance."""
        # First add some credits
        await service.add_credits("user-123", Decimal("20.00"), "Purchase")

        # Then deduct
        tx = await service.deduct_credits(
            user_id="user-123",
            amount=Decimal("10.00"),
            reason="Debate usage",
        )
        assert tx.amount == Decimal("-10.00")
        assert tx.type == TransactionType.USAGE

        balance = await service.get_balance("user-123")
        assert balance.balance == Decimal("15.00")  # 25 - 10

    @pytest.mark.asyncio
    async def test_deduct_credits_with_reference(self, service):
        """Should store reference ID for deductions."""
        tx = await service.deduct_credits(
            user_id="user-123",
            amount=Decimal("2.00"),
            reason="Debate: What is AI?",
            reference_id="debate-789",
        )
        assert tx.reference_id == "debate-789"

    @pytest.mark.asyncio
    async def test_deduct_insufficient_credits(self, service):
        """Should raise error when insufficient credits."""
        with pytest.raises(InsufficientCreditsError) as exc_info:
            await service.deduct_credits(
                user_id="user-123",
                amount=Decimal("100.00"),
                reason="Big debate",
            )
        assert exc_info.value.details["available"] == "5.00"
        assert exc_info.value.details["required"] == "100.00"
        assert exc_info.value.details["shortfall"] == "95.00"

    @pytest.mark.asyncio
    async def test_deduct_credits_invalid_amount(self, service):
        """Should reject zero or negative deduction amounts."""
        with pytest.raises(InvalidAmountError):
            await service.deduct_credits(
                user_id="user-123",
                amount=Decimal("0"),
                reason="Invalid",
            )

    @pytest.mark.asyncio
    async def test_check_sufficient_credits_true(self, service):
        """Should return True when user has enough credits."""
        result = await service.check_sufficient_credits("user-123", Decimal("5.00"))
        assert result is True

    @pytest.mark.asyncio
    async def test_check_sufficient_credits_false(self, service):
        """Should return False when user lacks credits."""
        result = await service.check_sufficient_credits("user-123", Decimal("10.00"))
        assert result is False

    @pytest.mark.asyncio
    async def test_check_sufficient_credits_exact(self, service):
        """Should return True for exact balance match."""
        result = await service.check_sufficient_credits("user-123", Decimal("5.00"))
        assert result is True

    @pytest.mark.asyncio
    async def test_transaction_history_empty(self, service):
        """New users should have empty transaction history."""
        history = await service.get_transaction_history("new-user")
        assert history == []

    @pytest.mark.asyncio
    async def test_transaction_history(self, service):
        """Should track transaction history."""
        await service.add_credits("user-123", Decimal("20.00"), "Purchase")
        await service.deduct_credits("user-123", Decimal("5.00"), "Usage")

        history = await service.get_transaction_history("user-123")
        assert len(history) == 2
        assert history[0].amount == Decimal("-5.00")  # Most recent first
        assert history[1].amount == Decimal("20.00")

    @pytest.mark.asyncio
    async def test_transaction_history_limit(self, service):
        """Should respect limit parameter."""
        for i in range(5):
            await service.add_credits("user-123", Decimal("1.00"), f"Credit {i}")

        history = await service.get_transaction_history("user-123", limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_transaction_history_offset(self, service):
        """Should respect offset parameter."""
        for i in range(5):
            await service.add_credits("user-123", Decimal("1.00"), f"Credit {i}")

        history = await service.get_transaction_history("user-123", offset=2)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_estimate_cost_anthropic(self, service):
        """Should estimate cost for Anthropic."""
        cost = await service.estimate_cost("anthropic", "claude-3-5-sonnet", 10000)
        # 10000 tokens * 0.015 per 1k = 0.15
        assert cost == Decimal("0.15")

    @pytest.mark.asyncio
    async def test_estimate_cost_openai(self, service):
        """Should estimate cost for OpenAI."""
        cost = await service.estimate_cost("openai", "gpt-4", 5000)
        # 5000 tokens * 0.010 per 1k = 0.05
        assert cost == Decimal("0.05")

    @pytest.mark.asyncio
    async def test_estimate_cost_google(self, service):
        """Should estimate cost for Google/Gemini."""
        cost = await service.estimate_cost("google", "gemini-pro", 20000)
        # 20000 tokens * 0.005 per 1k = 0.10
        assert cost == Decimal("0.10")

    @pytest.mark.asyncio
    async def test_estimate_cost_unknown_provider(self, service):
        """Should use default rate for unknown providers."""
        cost = await service.estimate_cost("unknown", "model", 10000)
        # 10000 tokens * 0.010 per 1k = 0.10
        assert cost == Decimal("0.10")

    @pytest.mark.asyncio
    async def test_transaction_records_balance_before_after(self, service):
        """Transactions should record balance before and after."""
        tx = await service.add_credits("user-123", Decimal("20.00"), "Purchase")
        assert tx.balance_before == Decimal("5.00")
        assert tx.balance_after == Decimal("25.00")


class TestGetBillingService:
    def test_returns_singleton(self):
        """Should return the same instance."""
        # Reset the singleton for this test
        import modules.billing.service as svc
        svc._service_instance = None

        service1 = get_billing_service()
        service2 = get_billing_service()
        assert service1 is service2

    def test_returns_billing_service_instance(self):
        """Should return a BillingService instance."""
        import modules.billing.service as svc
        svc._service_instance = None

        service = get_billing_service()
        assert isinstance(service, BillingService)

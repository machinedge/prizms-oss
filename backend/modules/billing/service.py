"""
Billing service stub implementation.

This is a stub that will be completed in Stories 16 and 17.
It provides a working in-memory implementation for testing.
"""

from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone
import uuid

from .interfaces import IBillingService
from .models import (
    CreditBalance,
    Transaction,
    TransactionType,
    SubscriptionTier,
)
from .exceptions import InsufficientCreditsError, InvalidAmountError


class BillingService(IBillingService):
    """
    Stub implementation of the billing service.

    Uses in-memory storage for testing. Will be replaced with
    Supabase + Stripe implementation in Stories 16-17.
    """

    def __init__(self):
        # In-memory storage for testing
        self._balances: dict[str, Decimal] = {}
        self._transactions: dict[str, list[Transaction]] = {}

    async def get_balance(self, user_id: str) -> CreditBalance:
        """Get user's credit balance."""
        balance = self._balances.get(user_id, Decimal("5.00"))  # Default $5 free tier

        return CreditBalance(
            user_id=user_id,
            balance=balance,
            tier=SubscriptionTier.FREE,
            monthly_allowance=Decimal("5.00"),
            allowance_remaining=min(balance, Decimal("5.00")),
        )

    async def check_sufficient_credits(
        self,
        user_id: str,
        required_amount: Decimal,
    ) -> bool:
        """Check if user has enough credits."""
        balance = await self.get_balance(user_id)
        return balance.balance >= required_amount

    async def deduct_credits(
        self,
        user_id: str,
        amount: Decimal,
        reason: str,
        reference_id: Optional[str] = None,
    ) -> Transaction:
        """Deduct credits from user's balance."""
        if amount <= 0:
            raise InvalidAmountError(amount, "Amount must be positive")

        balance = await self.get_balance(user_id)

        if balance.balance < amount:
            raise InsufficientCreditsError(
                required=amount,
                available=balance.balance,
                user_id=user_id,
            )

        new_balance = balance.balance - amount
        self._balances[user_id] = new_balance

        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount=-amount,  # Negative for deduction
            type=TransactionType.USAGE,
            reason=reason,
            reference_id=reference_id,
            balance_before=balance.balance,
            balance_after=new_balance,
            created_at=datetime.now(timezone.utc),
        )

        if user_id not in self._transactions:
            self._transactions[user_id] = []
        self._transactions[user_id].insert(0, transaction)

        return transaction

    async def add_credits(
        self,
        user_id: str,
        amount: Decimal,
        reason: str,
        transaction_type: TransactionType = TransactionType.PURCHASE,
        stripe_payment_id: Optional[str] = None,
    ) -> Transaction:
        """Add credits to user's balance."""
        if amount <= 0:
            raise InvalidAmountError(amount, "Amount must be positive")

        balance = await self.get_balance(user_id)
        new_balance = balance.balance + amount
        self._balances[user_id] = new_balance

        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount=amount,
            type=transaction_type,
            reason=reason,
            reference_id=stripe_payment_id,
            balance_before=balance.balance,
            balance_after=new_balance,
            created_at=datetime.now(timezone.utc),
        )

        if user_id not in self._transactions:
            self._transactions[user_id] = []
        self._transactions[user_id].insert(0, transaction)

        return transaction

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        """Get user's transaction history."""
        transactions = self._transactions.get(user_id, [])
        return transactions[offset : offset + limit]

    async def estimate_cost(
        self,
        provider: str,
        model: str,
        estimated_tokens: int,
    ) -> Decimal:
        """Estimate operation cost."""
        # Simplified cost estimation
        # Real implementation will use provider-specific pricing
        cost_per_1k_tokens = {
            "anthropic": Decimal("0.015"),
            "openai": Decimal("0.010"),
            "google": Decimal("0.005"),
            "xai": Decimal("0.010"),
            "openrouter": Decimal("0.010"),
        }

        rate = cost_per_1k_tokens.get(provider, Decimal("0.010"))
        return (Decimal(estimated_tokens) / 1000) * rate


# Module-level instance getter
_service_instance: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    """Get the billing service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = BillingService()
    return _service_instance

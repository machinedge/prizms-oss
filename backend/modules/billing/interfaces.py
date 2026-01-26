"""
Billing module interface.

Other modules should depend on IBillingService, not the concrete implementation.
This enables the debates module to check/deduct credits without knowing about Stripe.
"""

from typing import Protocol, Optional, runtime_checkable
from decimal import Decimal

from .models import CreditBalance, Transaction, TransactionType


@runtime_checkable
class IBillingService(Protocol):
    """
    Interface for billing and credit operations.

    This protocol defines the contract that the billing module exposes
    to other modules. The debates module uses this to manage credits.
    """

    async def get_balance(self, user_id: str) -> CreditBalance:
        """
        Get a user's current credit balance.

        Args:
            user_id: Supabase user ID (UUID)

        Returns:
            CreditBalance with current balance and tier info

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        ...

    async def check_sufficient_credits(
        self,
        user_id: str,
        required_amount: Decimal,
    ) -> bool:
        """
        Check if a user has sufficient credits for an operation.

        This is a non-blocking check - it doesn't reserve the credits.
        Use this before starting an operation to fail fast.

        Args:
            user_id: Supabase user ID
            required_amount: Amount of credits needed

        Returns:
            True if user has enough credits, False otherwise
        """
        ...

    async def deduct_credits(
        self,
        user_id: str,
        amount: Decimal,
        reason: str,
        reference_id: Optional[str] = None,
    ) -> Transaction:
        """
        Deduct credits from a user's balance.

        Args:
            user_id: Supabase user ID
            amount: Amount to deduct (must be positive)
            reason: Human-readable reason for the deduction
            reference_id: Optional reference (e.g., debate_id)

        Returns:
            Transaction record of the deduction

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            ValidationError: If amount is invalid
        """
        ...

    async def add_credits(
        self,
        user_id: str,
        amount: Decimal,
        reason: str,
        transaction_type: TransactionType = TransactionType.PURCHASE,
        stripe_payment_id: Optional[str] = None,
    ) -> Transaction:
        """
        Add credits to a user's balance.

        Args:
            user_id: Supabase user ID
            amount: Amount to add (must be positive)
            reason: Human-readable reason for the addition
            transaction_type: Type of transaction (purchase, refund, free_tier)
            stripe_payment_id: Stripe payment ID if applicable

        Returns:
            Transaction record of the addition

        Raises:
            ValidationError: If amount is invalid
        """
        ...

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        """
        Get a user's credit transaction history.

        Args:
            user_id: Supabase user ID
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip

        Returns:
            List of transactions, most recent first
        """
        ...

    async def estimate_cost(
        self,
        provider: str,
        model: str,
        estimated_tokens: int,
    ) -> Decimal:
        """
        Estimate the cost of an operation before running it.

        This is used to check if a user has enough credits before
        starting a debate.

        Args:
            provider: LLM provider name (e.g., "anthropic")
            model: Model identifier (e.g., "claude-3-5-sonnet")
            estimated_tokens: Estimated token count

        Returns:
            Estimated cost in credits (USD)
        """
        ...

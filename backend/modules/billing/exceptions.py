"""
Billing module exceptions.

These exceptions are raised by the billing module and can be caught
by API error handlers to return appropriate HTTP responses.
"""

from decimal import Decimal
from typing import Optional

from shared.exceptions import PrizmsError, ValidationError


class BillingError(PrizmsError):
    """Base exception for billing-related errors."""

    pass


class InsufficientCreditsError(BillingError):
    """
    Raised when a user doesn't have enough credits for an operation.

    This is a common error that the UI should handle gracefully
    by prompting the user to purchase more credits.
    """

    def __init__(
        self,
        required: Decimal,
        available: Decimal,
        user_id: Optional[str] = None,
    ):
        message = f"Insufficient credits. Required: ${required}, available: ${available}"
        super().__init__(
            message,
            code="INSUFFICIENT_CREDITS",
            details={
                "required": str(required),
                "available": str(available),
                "shortfall": str(required - available),
            },
        )
        if user_id:
            self.details["user_id"] = user_id


class InvalidAmountError(ValidationError):
    """Raised when a credit amount is invalid."""

    def __init__(self, amount: Decimal, reason: str):
        super().__init__(
            f"Invalid amount: {amount}. {reason}",
            code="INVALID_AMOUNT",
            details={"amount": str(amount), "reason": reason},
        )


class PaymentFailedError(BillingError):
    """Raised when a payment fails."""

    def __init__(self, message: str, stripe_error: Optional[str] = None):
        super().__init__(
            message,
            code="PAYMENT_FAILED",
            details={"stripe_error": stripe_error} if stripe_error else {},
        )


class WebhookVerificationError(BillingError):
    """Raised when Stripe webhook signature verification fails."""

    def __init__(self):
        super().__init__(
            "Webhook signature verification failed",
            code="WEBHOOK_VERIFICATION_FAILED",
        )


class DuplicateTransactionError(BillingError):
    """Raised when attempting to process a duplicate transaction."""

    def __init__(self, transaction_id: str):
        super().__init__(
            f"Transaction already processed: {transaction_id}",
            code="DUPLICATE_TRANSACTION",
            details={"transaction_id": transaction_id},
        )

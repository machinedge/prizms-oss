"""Tests for billing module exceptions."""

import pytest
from decimal import Decimal

from modules.billing.exceptions import (
    BillingError,
    InsufficientCreditsError,
    InvalidAmountError,
    PaymentFailedError,
    WebhookVerificationError,
    DuplicateTransactionError,
)


class TestBillingError:
    def test_billing_error(self):
        """Should create a base billing error."""
        error = BillingError("Something went wrong", code="BILLING_ERROR")
        assert str(error) == "Something went wrong"
        assert error.code == "BILLING_ERROR"

    def test_billing_error_to_dict(self):
        """Should convert to dict for API responses."""
        error = BillingError("Test error", code="TEST", details={"key": "value"})
        result = error.to_dict()
        assert result["error"] == "TEST"
        assert result["message"] == "Test error"
        assert result["details"]["key"] == "value"


class TestInsufficientCreditsError:
    def test_insufficient_credits_error(self):
        """Should create insufficient credits error with details."""
        error = InsufficientCreditsError(
            required=Decimal("10.00"),
            available=Decimal("5.00"),
        )
        assert "Insufficient credits" in str(error)
        assert error.code == "INSUFFICIENT_CREDITS"
        assert error.details["required"] == "10.00"
        assert error.details["available"] == "5.00"
        assert error.details["shortfall"] == "5.00"

    def test_insufficient_credits_with_user_id(self):
        """Should include user ID in details when provided."""
        error = InsufficientCreditsError(
            required=Decimal("20.00"),
            available=Decimal("5.00"),
            user_id="user-123",
        )
        assert error.details["user_id"] == "user-123"


class TestInvalidAmountError:
    def test_invalid_amount_error(self):
        """Should create invalid amount error."""
        error = InvalidAmountError(
            amount=Decimal("-5.00"),
            reason="Amount must be positive",
        )
        assert "Invalid amount" in str(error)
        assert error.code == "INVALID_AMOUNT"
        assert error.details["amount"] == "-5.00"
        assert error.details["reason"] == "Amount must be positive"


class TestPaymentFailedError:
    def test_payment_failed_error(self):
        """Should create payment failed error."""
        error = PaymentFailedError("Card declined")
        assert str(error) == "Card declined"
        assert error.code == "PAYMENT_FAILED"

    def test_payment_failed_with_stripe_error(self):
        """Should include Stripe error when provided."""
        error = PaymentFailedError(
            "Payment failed",
            stripe_error="card_declined",
        )
        assert error.details["stripe_error"] == "card_declined"


class TestWebhookVerificationError:
    def test_webhook_verification_error(self):
        """Should create webhook verification error."""
        error = WebhookVerificationError()
        assert "Webhook signature verification failed" in str(error)
        assert error.code == "WEBHOOK_VERIFICATION_FAILED"


class TestDuplicateTransactionError:
    def test_duplicate_transaction_error(self):
        """Should create duplicate transaction error."""
        error = DuplicateTransactionError("tx-123")
        assert "Transaction already processed" in str(error)
        assert error.code == "DUPLICATE_TRANSACTION"
        assert error.details["transaction_id"] == "tx-123"

"""
Billing module.

Handles Stripe integration, credit management, and payment processing.

Public API:
- IBillingService: Interface for billing operations
- CreditBalance: User's credit balance
- Transaction: Credit transaction record
- Billing exceptions: InsufficientCreditsError, etc.
"""

from .interfaces import IBillingService
from .models import (
    CreditBalance,
    Transaction,
    TransactionType,
    SubscriptionTier,
    CreditPack,
    CheckoutSession,
    DEFAULT_CREDIT_PACKS,
)
from .exceptions import (
    BillingError,
    InsufficientCreditsError,
    InvalidAmountError,
    PaymentFailedError,
    WebhookVerificationError,
    DuplicateTransactionError,
)

__all__ = [
    # Interface
    "IBillingService",
    # Models
    "CreditBalance",
    "Transaction",
    "TransactionType",
    "SubscriptionTier",
    "CreditPack",
    "CheckoutSession",
    "DEFAULT_CREDIT_PACKS",
    # Exceptions
    "BillingError",
    "InsufficientCreditsError",
    "InvalidAmountError",
    "PaymentFailedError",
    "WebhookVerificationError",
    "DuplicateTransactionError",
]

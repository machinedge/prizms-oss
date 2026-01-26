"""
Billing module data models.

These models define the data structures used by the billing module
and exposed to other modules through the interface.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    """Types of credit transactions."""

    PURCHASE = "purchase"      # User bought credits
    USAGE = "usage"            # Credits used for a debate
    FREE_TIER = "free_tier"    # Monthly free credits
    REFUND = "refund"          # Refund for failed operation
    ADJUSTMENT = "adjustment"  # Manual adjustment by admin


class SubscriptionTier(str, Enum):
    """User subscription tiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class CreditBalance(BaseModel):
    """
    A user's current credit balance and tier info.

    Credits are denominated in USD (e.g., 5.00 = $5.00 in credits).
    """

    user_id: str = Field(..., description="User ID")
    balance: Decimal = Field(..., description="Current credit balance in USD")
    tier: SubscriptionTier = Field(
        default=SubscriptionTier.FREE,
        description="User's subscription tier",
    )
    monthly_allowance: Decimal = Field(
        default=Decimal("5.00"),
        description="Monthly free credit allowance",
    )
    allowance_remaining: Decimal = Field(
        default=Decimal("5.00"),
        description="Remaining monthly allowance",
    )
    allowance_resets_at: Optional[datetime] = Field(
        None,
        description="When the monthly allowance resets",
    )


class Transaction(BaseModel):
    """
    A credit transaction record.

    Tracks all changes to a user's credit balance.
    """

    id: str = Field(..., description="Transaction ID (UUID)")
    user_id: str = Field(..., description="User ID")
    amount: Decimal = Field(
        ...,
        description="Transaction amount (positive for add, negative for deduct)",
    )
    type: TransactionType = Field(..., description="Transaction type")
    reason: str = Field(..., description="Human-readable reason")
    reference_id: Optional[str] = Field(
        None,
        description="Reference ID (e.g., debate_id, stripe_payment_id)",
    )
    balance_before: Decimal = Field(..., description="Balance before transaction")
    balance_after: Decimal = Field(..., description="Balance after transaction")
    created_at: datetime = Field(..., description="Transaction timestamp")


class CreditPack(BaseModel):
    """
    A purchasable credit pack.

    Defines the credit packs available for purchase.
    """

    id: str = Field(..., description="Pack ID (matches Stripe price ID)")
    name: str = Field(..., description="Display name")
    amount: Decimal = Field(..., description="Credit amount in USD")
    price: Decimal = Field(..., description="Purchase price in USD")
    description: Optional[str] = Field(None, description="Pack description")
    popular: bool = Field(default=False, description="Whether to highlight this pack")


# Default credit packs
DEFAULT_CREDIT_PACKS = [
    CreditPack(
        id="pack_20",
        name="Starter Pack",
        amount=Decimal("20.00"),
        price=Decimal("20.00"),
        description="$20 in credits",
        popular=True,
    ),
    CreditPack(
        id="pack_50",
        name="Value Pack",
        amount=Decimal("55.00"),  # 10% bonus
        price=Decimal("50.00"),
        description="$55 in credits (10% bonus)",
    ),
    CreditPack(
        id="pack_100",
        name="Power Pack",
        amount=Decimal("120.00"),  # 20% bonus
        price=Decimal("100.00"),
        description="$120 in credits (20% bonus)",
    ),
]


class CheckoutSession(BaseModel):
    """
    Stripe checkout session info.

    Returned when initiating a credit purchase.
    """

    session_id: str = Field(..., description="Stripe checkout session ID")
    url: str = Field(..., description="Checkout URL to redirect user to")


class PurchaseRequest(BaseModel):
    """Request to purchase credits."""

    pack_id: str = Field(..., description="Credit pack ID to purchase")


class BalanceResponse(BaseModel):
    """API response for balance queries."""

    balance: Decimal = Field(..., description="Current balance")
    currency: str = Field(default="USD", description="Currency code")
    tier: SubscriptionTier = Field(..., description="Subscription tier")


class TransactionListResponse(BaseModel):
    """API response for transaction history."""

    transactions: list[Transaction] = Field(..., description="Transaction list")
    total: int = Field(..., description="Total transaction count")
    has_more: bool = Field(..., description="Whether more transactions exist")

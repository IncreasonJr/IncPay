from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TransactionStatus(str, Enum):
    """Lifecycle status of a transaction."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class TransactionBase(BaseModel):
    """
    Base attributes for a transaction on IncPay.
    All monetary amounts are represented in Ghanaian Cedis (GHS / ₵).
    """
    seller_id: UUID = Field(..., description="ID of the seller receiving payout")
    coupon_id: UUID = Field(..., description="ID of the coupon scanned/used")
    paystack_reference: str = Field(..., description="Unique Paystack payment reference")
    currency: str = Field(default="GHS", description="Transaction currency (always GHS for IncPay)")
    listed_amount: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Original listed price of the item/service in Ghanaian Cedis (₵)",
    )
    customer_discount_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        decimal_places=2,
        description="Discount deducted for the customer (D/2) in Ghanaian Cedis (₵)",
    )
    amount_paid: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Amount actually paid by the customer in Ghanaian Cedis (₵)",
    )
    platform_cut_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        decimal_places=2,
        description="IncPay platform revenue cut (D/2) in Ghanaian Cedis (₵)",
    )
    seller_payout_amount: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Amount routed to the seller's account in Ghanaian Cedis (₵)",
    )
    status: TransactionStatus = Field(
        default=TransactionStatus.PENDING,
        description="Payment status: pending, success, or failed",
    )
    customer_email: Optional[str] = Field(
        None,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Customer email address",
    )


class TransactionCreate(TransactionBase):
    """
    Payload for creating a new transaction record.
    Provides a helper to accurately calculate D/2 splits in Cedis (₵).
    """

    @classmethod
    def calculate_split(
        cls,
        listed_amount: Decimal,
        agreed_discount: Decimal,
    ) -> Dict[str, Decimal]:
        """
        Calculate the exact payment-bridge split for IncPay in Ghanaian Cedis (₵).

        Business Model:
        - Agreed discount: D % (agreed_discount)
        - Customer visible discount: D / 2 %
        - Platform cut: D / 2 %
        - Seller payout: Listed - (2 * customer_discount)

        Example:
        - listed_amount = ₵10,000.00, agreed_discount = 20.00%
        - customer_discount_amount = ₵1,000.00
        - amount_paid = ₵9,000.00
        - platform_cut_amount = ₵1,000.00
        - seller_payout_amount = ₵8,000.00
        """
        quantize_two_places = Decimal("0.01")
        listed = listed_amount.quantize(quantize_two_places, rounding=ROUND_HALF_UP)

        # Half the agreed discount passed to customer
        half_discount_rate = (agreed_discount / Decimal("200.00"))
        customer_discount = (listed * half_discount_rate).quantize(quantize_two_places, rounding=ROUND_HALF_UP)

        # Customer pays listed price minus visible discount
        amount_paid = (listed - customer_discount).quantize(quantize_two_places, rounding=ROUND_HALF_UP)

        # IncPay retains the other half of D
        platform_cut = customer_discount

        # Seller receives the remainder of what the customer paid
        seller_payout = (amount_paid - platform_cut).quantize(quantize_two_places, rounding=ROUND_HALF_UP)

        return {
            "listed_amount": listed,
            "customer_discount_amount": customer_discount,
            "amount_paid": amount_paid,
            "platform_cut_amount": platform_cut,
            "seller_payout_amount": seller_payout,
        }

    @model_validator(mode="after")
    def validate_amounts_balance(self) -> "TransactionCreate":
        """Verify that amount_paid equals platform_cut + seller_payout in Cedis (₵)."""
        expected_paid = (self.platform_cut_amount + self.seller_payout_amount).quantize(Decimal("0.01"))
        actual_paid = self.amount_paid.quantize(Decimal("0.01"))
        if abs(expected_paid - actual_paid) > Decimal("0.02"):
            raise ValueError(
                f"Financial imbalance: amount_paid (₵{actual_paid}) must equal "
                f"platform_cut (₵{self.platform_cut_amount}) + seller_payout (₵{self.seller_payout_amount})"
            )
        return self


class TransactionResponse(TransactionBase):
    """Schema returned for transaction queries."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

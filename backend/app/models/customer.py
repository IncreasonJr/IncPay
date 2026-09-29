from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CustomerSignupRequest(BaseModel):
    """Payload for customer account registration."""
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="Customer email address")
    password: str = Field(..., min_length=8, description="Password (at least 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=150, description="Customer full name")
    phone: Optional[str] = Field(None, max_length=30, description="Customer phone number (optional)")


class CustomerResponse(BaseModel):
    """Customer profile details including their personal coupon identity."""
    id: UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    coupon_token: str
    verbal_code: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerTransactionItem(BaseModel):
    """Customer-facing transaction history item."""
    id: UUID
    created_at: datetime
    business_name: str
    currency: str = "GHS"
    listed_amount: Decimal
    customer_discount_amount: Decimal
    amount_paid: Decimal
    paystack_reference: str
    status: str
    receipt_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerTransactionsResponse(BaseModel):
    """Paginated list of customer transactions."""
    transactions: List[CustomerTransactionItem]
    total: int
    page: int
    limit: int

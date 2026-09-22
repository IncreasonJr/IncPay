from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SellerBase(BaseModel):
    """
    Base attributes for an IncPay seller.
    Amounts and percentages are in Ghanaian context.
    agreed_discount is D (%) where 0 < D < 100.
    """
    business_name: str = Field(..., min_length=1, description="Registered or trading business name")
    contact_email: str = Field(
        ...,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Primary contact email for notifications",
    )
    contact_phone: Optional[str] = Field(None, description="Contact phone number (e.g. +233...)")
    agreed_discount: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        lt=Decimal("100.00"),
        decimal_places=2,
        description="Total agreed discount percentage D (e.g. 20.00 for 20%)",
    )
    is_active: bool = Field(default=True, description="Whether the seller is actively accepting payments")

    @field_validator("agreed_discount")
    @classmethod
    def validate_agreed_discount(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0.00") or value >= Decimal("100.00"):
            raise ValueError("agreed_discount must be strictly between 0 and 100 (exclusive).")
        return round(value, 2)


class SellerCreate(SellerBase):
    """Payload for creating a new seller."""
    paystack_subaccount_code: Optional[str] = Field(None, description="Paystack subaccount code (e.g. ACCT_...)")
    paystack_subaccount_id: Optional[str] = Field(None, description="Paystack subaccount ID")


class SellerUpdate(BaseModel):
    """Payload for updating an existing seller. All fields are optional."""
    business_name: Optional[str] = Field(None, min_length=1)
    contact_email: Optional[str] = Field(None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    contact_phone: Optional[str] = None
    agreed_discount: Optional[Decimal] = Field(None, gt=Decimal("0.00"), lt=Decimal("100.00"), decimal_places=2)
    paystack_subaccount_code: Optional[str] = None
    paystack_subaccount_id: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("agreed_discount")
    @classmethod
    def validate_agreed_discount(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None:
            if value <= Decimal("0.00") or value >= Decimal("100.00"):
                raise ValueError("agreed_discount must be strictly between 0 and 100 (exclusive).")
            return round(value, 2)
        return value


class SellerResponse(SellerBase):
    """Schema returned for seller records."""
    id: UUID
    paystack_subaccount_code: Optional[str] = None
    paystack_subaccount_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

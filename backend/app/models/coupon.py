from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CouponBase(BaseModel):
    """
    Base attributes for a coupon/QR code.
    Identifies a seller's payment landing point on IncPay.
    """
    seller_id: UUID = Field(..., description="ID of the associated seller")
    code: str = Field(..., min_length=2, max_length=50, description="Unique coupon code used in QR links")
    is_active: bool = Field(default=True, description="Whether this coupon is active for checkouts")

    @field_validator("code")
    @classmethod
    def sanitize_code(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Coupon code cannot be empty.")
        return cleaned


class CouponCreate(CouponBase):
    """Payload for generating a new coupon for a seller."""
    pass


class CouponResponse(CouponBase):
    """Schema returned for coupon records."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

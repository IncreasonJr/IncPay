import logging
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services import (
    coupon_service,
    paystack_service,
    receipt_service,
    seller_service,
    transaction_service,
)
from app.services.paystack_service import PaystackError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payments"])


class PublicCouponResponse(BaseModel):
    """Sanitized public metadata for a coupon."""
    business_name: str
    agreed_discount: float
    customer_discount: float
    is_active: bool


class PaymentInitializeRequest(BaseModel):
    """Payload for initializing a checkout payment."""
    coupon_code: str = Field(..., min_length=2, max_length=50, description="Seller coupon code")
    listed_amount: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Original listed bill amount before discount in GHS (₵)",
    )
    email: Optional[str] = Field(None, description="Customer contact email for payment receipt")


class PaymentInitializeResponse(BaseModel):
    """Response containing Paystack transaction credentials and calculated amounts."""
    authorization_url: str
    access_code: str
    reference: str
    amount_paid: float
    listed_amount: float
    discount_amount: float


@router.get(
    "/api/public/coupon/{code}",
    response_model=PublicCouponResponse,
    summary="Public coupon lookup",
)
def get_public_coupon(code: str) -> PublicCouponResponse:
    """
    Look up coupon and return safe public merchant details.
    No authentication required.
    Does NOT leak merchant contact emails, phone numbers, or subaccount keys.
    """
    coupon = coupon_service.get_coupon_by_code(code)
    if not coupon or not coupon.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired coupon.",
        )

    business_name = coupon.get("business_name") or "Merchant Partner"
    agreed_discount = float(coupon.get("agreed_discount") or 0.0)
    customer_discount = round(agreed_discount / 2.0, 2)

    return PublicCouponResponse(
        business_name=business_name,
        agreed_discount=agreed_discount,
        customer_discount=customer_discount,
        is_active=True,
    )


@router.post(
    "/api/public/initialize-payment",
    response_model=PaymentInitializeResponse,
    summary="Initialize Paystack payment checkout",
)
def initialize_payment(request: PaymentInitializeRequest) -> PaymentInitializeResponse:
    """
    Initialize a customer payment checkout session.
    No authentication required.
    Server strictly recalculates all payable amounts from the verified seller discount D.
    """
    settings = get_settings()

    # 1. Validate minimum payment amount
    min_amount = Decimal(str(settings.MIN_PAYMENT_AMOUNT))
    if request.listed_amount < min_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum payment amount is ₵{settings.MIN_PAYMENT_AMOUNT:.2f}",
        )

    # 2. Look up coupon and verify merchant
    coupon = coupon_service.get_coupon_by_code(request.coupon_code)
    if not coupon or not coupon.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired coupon.",
        )

    subaccount_code = coupon.get("paystack_subaccount_code")
    if not subaccount_code:
        logger.error(f"Coupon {request.coupon_code} missing seller paystack_subaccount_code.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merchant settlement subaccount is not configured.",
        )

    # 3. Server-side financial calculation (DO NOT trust client amounts)
    raw_d = coupon.get("agreed_discount") or "0.00"
    agreed_d = Decimal(str(raw_d))
    # Customer gets D/2 discount: listed_amount * (D / 200)
    customer_discount_amount = round(request.listed_amount * (agreed_d / Decimal("200.00")), 2)
    amount_paid = request.listed_amount - customer_discount_amount

    if amount_paid <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payable amount must be greater than zero.",
        )

    # 4. Email validation & fallback
    email = request.email.strip() if request.email and "@" in request.email else "noreply@incpay.app"

    # 5. Unique reference
    reference = f"INCPAY-{uuid4().hex.upper()}"

    metadata = {
        "coupon_code": coupon.get("code"),
        "seller_id": str(coupon.get("seller_id", "")),
        "business_name": coupon.get("business_name"),
        "listed_amount": float(request.listed_amount),
        "customer_discount_amount": float(customer_discount_amount),
        "amount_paid": float(amount_paid),
    }

    # 6. Initialize Paystack split transaction
    try:
        tx_data = paystack_service.initialize_transaction(
            email=email,
            amount_ghs=amount_paid,
            reference=reference,
            subaccount_code=subaccount_code,
            metadata=metadata,
        )

        auth_url = tx_data.get("authorization_url", "")
        access_code = tx_data.get("access_code", "")
        returned_ref = tx_data.get("reference", reference)

        return PaymentInitializeResponse(
            authorization_url=auth_url,
            access_code=access_code,
            reference=returned_ref,
            amount_paid=float(amount_paid),
            listed_amount=float(request.listed_amount),
            discount_amount=float(customer_discount_amount),
        )

    except PaystackError as exc:
        logger.error(f"Paystack transaction initialization failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment initialization failed: {exc.message}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error initializing payment: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initializing payment: {str(exc)}",
        )


class PaymentVerifyResponse(BaseModel):
    """Sanitized public verification details for customer receipt confirmation."""
    status: str
    amount_paid: float
    reference: str
    customer_email: Optional[str] = None


@router.get(
    "/api/public/verify-payment/{reference}",
    response_model=PaymentVerifyResponse,
    summary="Verify payment reference with Paystack",
)
def verify_payment(reference: str) -> PaymentVerifyResponse:
    """
    Public endpoint to verify payment status with Paystack by reference.
    Used by customer checkout success screen to confirm settlement.
    Does NOT leak merchant credentials, margin splits, or subaccounts.
    """
    try:
        data = paystack_service.verify_transaction(reference)
        status_val = data.get("status", "unknown")
        amount_pesewas = data.get("amount", 0)
        amount_paid = round(float(amount_pesewas) / 100.0, 2)
        ref_val = data.get("reference", reference)

        customer = data.get("customer") or {}
        cust_email = customer.get("email")
        if cust_email and cust_email.lower() == "noreply@incpay.app":
            cust_email = None

        return PaymentVerifyResponse(
            status=status_val,
            amount_paid=amount_paid,
            reference=ref_val,
            customer_email=cust_email,
        )
    except PaystackError as exc:
        logger.warning(f"Paystack verification error for reference '{reference}': {exc}")
        # Check if transaction was already logged/persisted in database
        tx = transaction_service.get_transaction_by_reference(reference)
        if tx:
            c_email = tx.customer_email
            if c_email and c_email.lower() == "noreply@incpay.app":
                c_email = None
            return PaymentVerifyResponse(
                status=tx.status.value,
                amount_paid=float(tx.amount_paid),
                reference=tx.paystack_reference,
                customer_email=c_email,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction reference '{reference}' not found.",
        )
    except Exception as exc:
        logger.error(f"Unexpected error verifying reference '{reference}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying payment transaction.",
        )


@router.get(
    "/api/public/receipt/{reference}",
    summary="Download payment receipt PDF",
    response_class=Response,
)
def download_receipt(reference: str) -> Response:
    """
    Public endpoint to view or download an official PDF payment receipt.
    No authentication required.
    Only confirmed, successful transactions can generate receipts.
    Sensitive merchant credentials or platform cut details are never exposed.
    """
    sanitized_ref = reference.strip()
    if not sanitized_ref or len(sanitized_ref) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment reference format.",
        )

    # 1. Lookup transaction
    tx = transaction_service.get_transaction_by_reference(sanitized_ref)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction reference '{sanitized_ref}' not found.",
        )

    # 2. Status verification
    tx_status = tx.status.value if hasattr(tx.status, "value") else str(tx.status)
    if tx_status != "success":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt unavailable: payment is not in a successful state.",
        )

    # 3. Lookup seller record
    seller = seller_service.get_seller_by_id(tx.seller_id)
    seller_dict: Dict[str, Any] = {}
    if seller:
        seller_dict = seller.model_dump()
    else:
        # Fallback to coupon lookup if seller record not directly accessible
        cp = coupon_service.get_active_coupon_for_seller(tx.seller_id)
        if cp:
            seller_dict["business_name"] = getattr(cp, "business_name", "Merchant Partner")

    tx_dict = tx.model_dump()

    # 4. Generate in-memory PDF
    try:
        pdf_bytes = receipt_service.generate_receipt_pdf(tx_dict, seller_dict)
    except Exception as exc:
        logger.error(f"Failed to generate receipt PDF for ref '{sanitized_ref}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating payment receipt PDF.",
        )

    # 5. Return PDF streaming response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="receipt-{sanitized_ref}.pdf"',
            "Content-Type": "application/pdf",
        },
    )



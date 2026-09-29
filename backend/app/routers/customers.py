import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status

from app.auth import verify_customer
from app.models.customer import (
    CustomerSignupRequest,
    CustomerResponse,
    CustomerTransactionsResponse,
)
from app.services.customer_service import (
    create_customer,
    get_customer_transactions,
)
from app.services.qr_service import generate_qr_png, generate_qr_svg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customer", tags=["Customer Accounts"])


@router.post(
    "/signup",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account",
)
def customer_signup(payload: CustomerSignupRequest):
    """
    Register a new customer account.
    Creates credentials in Supabase Auth and generates a personal IncPay coupon identity.
    """
    customer = create_customer(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    return customer


@router.get(
    "/me",
    response_model=CustomerResponse,
    summary="Get authenticated customer profile",
)
def get_current_customer(customer: dict = Depends(verify_customer)):
    """
    Retrieve details for the currently logged-in customer,
    including their signed coupon token and verbal verification code.
    """
    return customer


@router.get(
    "/me/transactions",
    response_model=CustomerTransactionsResponse,
    summary="List transactions for the authenticated customer",
)
def get_my_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    customer: dict = Depends(verify_customer),
):
    """
    Retrieve paginated transaction history linked to this customer's account.
    """
    return get_customer_transactions(customer_id=str(customer["id"]), page=page, limit=limit)


@router.get(
    "/me/coupon-qr",
    summary="Get customer digital coupon QR code",
)
def get_customer_coupon_qr(
    format: str = Query("png", pattern="^(png|svg)$", description="Format: png or svg"),
    customer: dict = Depends(verify_customer),
):
    """
    Generates a high-resolution QR code encoding the customer's personal coupon token.
    Used for scanning at merchant checkout to automatically log payments to customer history.
    """
    token = customer.get("coupon_token", "")
    if format == "svg":
        svg_content = generate_qr_svg(token)
        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={"Content-Disposition": f'inline; filename="incpay-coupon-{customer.get("verbal_code", "qr")}.svg"'},
        )
    else:
        png_bytes = generate_qr_png(token, box_size=12, border=3)
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f'inline; filename="incpay-coupon-{customer.get("verbal_code", "qr")}.png"'},
        )

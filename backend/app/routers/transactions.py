import logging
import math
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.auth import verify_admin
from app.services import email_service, log_service, receipt_service, seller_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Transactions"])


# --- Schemas ---

class TransactionSellerSummary(BaseModel):
    id: UUID
    business_name: str


class TransactionSellerDetail(BaseModel):
    id: UUID
    business_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    agreed_discount: Optional[Decimal] = None


class TransactionListItem(BaseModel):
    id: UUID
    seller_id: UUID
    seller: Optional[TransactionSellerSummary] = None
    listed_amount: Decimal
    discount_amount: Decimal
    customer_discount_amount: Optional[Decimal] = None
    amount_paid: Decimal
    platform_cut: Decimal
    platform_cut_amount: Optional[Decimal] = None
    seller_payout: Decimal
    seller_payout_amount: Optional[Decimal] = None
    paystack_reference: str
    customer_email: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class TransactionListResponse(BaseModel):
    transactions: List[TransactionListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionLogItem(BaseModel):
    id: UUID
    event_type: str
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime


class TransactionDetailResponse(BaseModel):
    id: UUID
    seller_id: UUID
    seller: Optional[TransactionSellerDetail] = None
    coupon_id: Optional[UUID] = None
    listed_amount: Decimal
    discount_amount: Decimal
    customer_discount_amount: Optional[Decimal] = None
    amount_paid: Decimal
    platform_cut: Decimal
    platform_cut_amount: Optional[Decimal] = None
    seller_payout: Decimal
    seller_payout_amount: Optional[Decimal] = None
    paystack_reference: str
    customer_email: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    logs: List[TransactionLogItem] = []


class ResendReceiptResponse(BaseModel):
    status: str
    recipient: str


# --- Endpoints ---

@router.get(
    "/api/transactions",
    response_model=TransactionListResponse,
    summary="List transactions with filters, pagination, and seller metadata (Admin)",
)
def list_transactions(
    seller_id: Optional[UUID] = Query(None, description="Filter by seller ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (success, failed, pending)"),
    start_date: Optional[str] = Query(None, description="Filter from start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to end date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search paystack reference or customer email"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    _: Any = Depends(verify_admin),
) -> TransactionListResponse:
    """
    Admin-only endpoint to list transactions.
    Supports filtering by seller, status, date range, and search keyword.
    Includes associated seller business name for each row.
    """
    items, total = transaction_service.list_transactions_filtered(
        seller_id=seller_id,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )

    # Fetch all sellers to map seller names efficiently
    try:
        all_sellers = seller_service.list_sellers(limit=1000)
        seller_map = {str(s.id): s.business_name for s in all_sellers}
    except Exception as exc:
        logger.warning(f"Could not bulk fetch sellers for transactions list: {exc}")
        seller_map = {}

    tx_list: List[TransactionListItem] = []
    for tx in items:
        s_id_str = str(tx.seller_id)
        seller_name = seller_map.get(s_id_str)
        if not seller_name:
            seller_record = seller_service.get_seller_by_id(tx.seller_id)
            seller_name = seller_record.business_name if seller_record else "Unknown Seller"
            seller_map[s_id_str] = seller_name

        seller_summary = TransactionSellerSummary(
            id=tx.seller_id,
            business_name=seller_name,
        )

        status_str = tx.status.value if hasattr(tx.status, "value") else str(tx.status)

        tx_list.append(
            TransactionListItem(
                id=tx.id,
                seller_id=tx.seller_id,
                seller=seller_summary,
                listed_amount=tx.listed_amount,
                discount_amount=tx.customer_discount_amount,
                customer_discount_amount=tx.customer_discount_amount,
                amount_paid=tx.amount_paid,
                platform_cut=tx.platform_cut_amount,
                platform_cut_amount=tx.platform_cut_amount,
                seller_payout=tx.seller_payout_amount,
                seller_payout_amount=tx.seller_payout_amount,
                paystack_reference=tx.paystack_reference,
                customer_email=tx.customer_email,
                status=status_str,
                created_at=tx.created_at,
                updated_at=tx.updated_at,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return TransactionListResponse(
        transactions=tx_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/api/transactions/{transaction_id}",
    response_model=TransactionDetailResponse,
    summary="Get transaction details with full seller info and event logs (Admin)",
)
def get_transaction_detail(
    transaction_id: UUID,
    _: Any = Depends(verify_admin),
) -> TransactionDetailResponse:
    """
    Admin-only endpoint to get full details for a specific transaction.
    Returns:
    - Transaction split amounts
    - Associated seller metadata
    - Chronological transaction audit logs (Paystack webhooks, receipt dispatches)
    """
    tx = transaction_service.get_transaction_by_id(transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found.",
        )

    # Fetch seller details
    seller = seller_service.get_seller_by_id(tx.seller_id)
    seller_detail: Optional[TransactionSellerDetail] = None
    if seller:
        seller_detail = TransactionSellerDetail(
            id=seller.id,
            business_name=seller.business_name,
            email=seller.contact_email,
            phone=seller.contact_phone,
            contact_email=seller.contact_email,
            contact_phone=seller.contact_phone,
            agreed_discount=seller.agreed_discount,
        )

    # Fetch audit logs ascending
    raw_logs = log_service.get_logs_for_transaction(transaction_id)
    log_items: List[TransactionLogItem] = [
        TransactionLogItem(
            id=log.id,
            event_type=log.event_type,
            payload=log.payload,
            created_at=log.created_at,
        )
        for log in raw_logs
    ]

    status_str = tx.status.value if hasattr(tx.status, "value") else str(tx.status)

    return TransactionDetailResponse(
        id=tx.id,
        seller_id=tx.seller_id,
        seller=seller_detail,
        coupon_id=tx.coupon_id,
        listed_amount=tx.listed_amount,
        discount_amount=tx.customer_discount_amount,
        customer_discount_amount=tx.customer_discount_amount,
        amount_paid=tx.amount_paid,
        platform_cut=tx.platform_cut_amount,
        platform_cut_amount=tx.platform_cut_amount,
        seller_payout=tx.seller_payout_amount,
        seller_payout_amount=tx.seller_payout_amount,
        paystack_reference=tx.paystack_reference,
        customer_email=tx.customer_email,
        status=status_str,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
        logs=log_items,
    )


@router.post(
    "/api/transactions/{transaction_id}/resend-receipt",
    response_model=ResendReceiptResponse,
    summary="Resend receipt PDF to customer email (Admin)",
)
def resend_receipt(
    transaction_id: UUID,
    _: Any = Depends(verify_admin),
) -> ResendReceiptResponse:
    """
    Admin-only endpoint to re-generate and resend the PDF receipt via email.
    Validations:
    - Transaction must exist
    - Transaction status must be 'success'
    - Customer email must be present and not 'noreply@incpay.app'
    Logs a 'receipt_resent' event to transaction_logs.
    """
    tx = transaction_service.get_transaction_by_id(transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found.",
        )

    status_str = tx.status.value if hasattr(tx.status, "value") else str(tx.status)
    if status_str != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resend receipt for unsuccessful or pending transactions.",
        )

    recipient = (tx.customer_email or "").strip()
    if not recipient or recipient.lower() == "noreply@incpay.app":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid customer email address on file for this transaction.",
        )

    # Fetch seller
    seller = seller_service.get_seller_by_id(tx.seller_id)
    seller_dict = seller.model_dump(mode="json") if seller else {"business_name": "Merchant Partner"}
    seller_name = seller.business_name if seller else "Merchant Partner"

    # Generate PDF in-memory
    tx_dict = tx.model_dump(mode="json")
    try:
        pdf_bytes = receipt_service.generate_receipt_pdf(tx_dict, seller_dict)
    except Exception as exc:
        logger.error(f"Failed to generate receipt PDF for tx '{transaction_id}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate receipt PDF.",
        )

    # Send email via Resend
    try:
        email_service.send_receipt_email(
            customer_email=recipient,
            seller_name=seller_name,
            pdf_bytes=pdf_bytes,
            reference=tx.paystack_reference,
        )
    except Exception as exc:
        logger.error(f"Failed to send receipt email to '{recipient}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to deliver receipt email: {str(exc)}",
        )

    # Log audit event
    log_service.log_event(
        event="receipt_resent",
        transaction_id=tx.id,
        payload={
            "recipient": recipient,
            "paystack_reference": tx.paystack_reference,
            "admin_action": True,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    return ResendReceiptResponse(status="sent", recipient=recipient)


@router.get(
    "/api/transactions/{transaction_id}/receipt",
    summary="Download receipt PDF for a transaction (Admin)",
    response_class=Response,
)
def download_transaction_receipt(
    transaction_id: UUID,
    _: Any = Depends(verify_admin),
) -> Response:
    """
    Admin-only endpoint to download the official PDF receipt for a transaction.
    Requires successful transaction status.
    """
    tx = transaction_service.get_transaction_by_id(transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found.",
        )

    status_str = tx.status.value if hasattr(tx.status, "value") else str(tx.status)
    if status_str != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt unavailable: transaction status is not successful.",
        )

    seller = seller_service.get_seller_by_id(tx.seller_id)
    seller_dict = seller.model_dump(mode="json") if seller else {"business_name": "Merchant Partner"}

    tx_dict = tx.model_dump(mode="json")
    try:
        pdf_bytes = receipt_service.generate_receipt_pdf(tx_dict, seller_dict)
    except Exception as exc:
        logger.error(f"Failed to generate receipt PDF for tx '{transaction_id}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating receipt PDF.",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="receipt-{tx.paystack_reference}.pdf"',
            "Content-Type": "application/pdf",
        },
    )

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from app.database import get_supabase_client
from app.models.transaction import TransactionCreate, TransactionResponse, TransactionStatus
from app.services import coupon_service, email_service, log_service, receipt_service, seller_service

logger = logging.getLogger(__name__)


def create_transaction(tx_data: TransactionCreate) -> Optional[TransactionResponse]:
    """
    Record a new payment-bridge transaction in Supabase.
    Amounts are stored in Ghanaian Cedis (numeric/Decimal).
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot create transaction.")
        return None

    try:
        # Decimal values are serialized to float/string or numeric representations for json
        payload = tx_data.model_dump(mode="json")
        res = client.table("transactions").insert(payload).execute()
        if res.data and len(res.data) > 0:
            return TransactionResponse.model_validate(res.data[0])
        logger.warning(f"No transaction returned after inserting reference '{tx_data.paystack_reference}'.")
        return None
    except Exception as exc:
        logger.error(f"Error creating transaction '{tx_data.paystack_reference}': {exc}")
        return None


def get_transaction_by_reference(reference: str) -> Optional[TransactionResponse]:
    """
    Retrieve a transaction record by its unique Paystack payment reference.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot fetch transaction.")
        return None

    try:
        res = client.table("transactions").select("*").eq("paystack_reference", reference).execute()
        if res.data and len(res.data) > 0:
            return TransactionResponse.model_validate(res.data[0])
        return None
    except Exception as exc:
        logger.error(f"Error fetching transaction reference '{reference}': {exc}")
        return None


def list_transactions(
    seller_id: Optional[Union[UUID, str]] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[TransactionResponse]:
    """
    List transactions, optionally filtered by seller ID, ordered by creation date descending.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot list transactions.")
        return []

    try:
        query = client.table("transactions").select("*")
        if seller_id is not None:
            query = query.eq("seller_id", str(seller_id))

        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        if res.data:
            return [TransactionResponse.model_validate(row) for row in res.data]
        return []
    except Exception as exc:
        logger.error(f"Error listing transactions: {exc}")
        return []


def update_transaction_status(
    reference: str,
    status: Union[TransactionStatus, str],
) -> Optional[TransactionResponse]:
    """
    Update the status of a transaction (e.g., pending -> success or failed).
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot update transaction status.")
        return None

    try:
        status_value = status.value if isinstance(status, TransactionStatus) else str(status)
        res = client.table("transactions").update({"status": status_value}).eq("paystack_reference", reference).execute()
        if res.data and len(res.data) > 0:
            return TransactionResponse.model_validate(res.data[0])
        logger.warning(f"No transaction found or updated for reference '{reference}'.")
        return None
    except Exception as exc:
        logger.error(f"Error updating transaction status for reference '{reference}': {exc}")
        return None


def _send_receipt_if_eligible(
    tx_data: Dict[str, Any],
    seller_id: Any,
    reference: str,
    customer_email: Optional[str],
    transaction_id: Optional[Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Safely generates and sends a receipt PDF via email if customer email is provided.
    Never raises an uncaught exception so the webhook execution is never disrupted.
    """
    if not customer_email or customer_email.strip().lower() == "noreply@incpay.app":
        return

    try:
        seller_record = seller_service.get_seller_by_id(seller_id) if seller_id else None
        if seller_record:
            seller_data = seller_record.model_dump()
        else:
            meta = metadata or {}
            seller_data = {
                "business_name": meta.get("business_name") or "Merchant Partner",
                "agreed_discount": meta.get("agreed_discount") or 20.0,
            }

        pdf_bytes = receipt_service.generate_receipt_pdf(tx_data, seller_data)
        seller_name = seller_data.get("business_name") or "Merchant Partner"
        email_service.send_receipt_email(customer_email, seller_name, pdf_bytes, reference)

        log_service.log_event(
            event="receipt_sent",
            transaction_id=transaction_id,
            payload={"customer_email": customer_email, "reference": reference},
        )
    except Exception as exc:
        logger.error(f"Failed to dispatch receipt email for ref '{reference}': {exc}")
        log_service.log_event(
            event="receipt_failed",
            transaction_id=transaction_id,
            payload={"error": str(exc), "customer_email": customer_email, "reference": reference},
        )


def create_transaction_from_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process incoming Paystack webhook payload and persist the verified transaction.
    - Extracts reference, amount (converted from pesewas to GHS), status, customer_email, metadata.
    - Idempotency: Returns existing record if duplicate paystack_reference is received.
    - Reconciliation safety: Reconciles status if Paystack updates payment outcome.
    - Recalculates split values from the seller's agreed discount and amount paid.
    - Always records raw event payload in transaction_logs.
    """
    raw_event = data.get("event", "")
    tx_payload = data.get("data") if isinstance(data.get("data"), dict) else data

    reference = tx_payload.get("reference")
    if not reference:
        logger.error("Webhook payload missing transaction reference.")
        log_service.log_event(event=raw_event or "webhook_missing_reference", payload=data)
        return {}

    # 1. Determine target transaction status
    status_str = str(tx_payload.get("status") or "").lower()
    if raw_event == "charge.failed" or status_str == "failed":
        target_status = TransactionStatus.FAILED
    elif raw_event == "charge.success" or status_str == "success":
        target_status = TransactionStatus.SUCCESS
    else:
        target_status = TransactionStatus.PENDING

    # 2. Check for existing transaction (Idempotency + Reconciliation)
    existing_tx = get_transaction_by_reference(reference)
    if existing_tx:
        # Always insert an audit record into transaction_logs
        log_service.log_event(
            event=raw_event or f"webhook_{target_status.value}",
            transaction_id=existing_tx.id,
            payload=data,
        )

        # Status reconciliation if status differs
        if existing_tx.status != target_status:
            logger.info(
                f"Reconciling status for reference '{reference}': "
                f"{existing_tx.status.value} -> {target_status.value}"
            )
            updated = update_transaction_status(reference, target_status)
            log_service.log_event(
                event="transaction_status_reconciled",
                transaction_id=existing_tx.id,
                payload={
                    "old_status": existing_tx.status.value,
                    "new_status": target_status.value,
                    "reference": reference,
                },
            )

            final_tx = updated or existing_tx
            if target_status == TransactionStatus.SUCCESS:
                _send_receipt_if_eligible(
                    tx_data=final_tx.model_dump(),
                    seller_id=final_tx.seller_id,
                    reference=reference,
                    customer_email=final_tx.customer_email,
                    transaction_id=existing_tx.id,
                    metadata=tx_payload.get("metadata"),
                )

            return final_tx.model_dump()

        logger.info(f"Duplicate webhook event received for reference '{reference}'. Ignoring duplicate.")
        return existing_tx.model_dump()

    # 3. Extract transaction details
    amount_pesewas = tx_payload.get("amount", 0)
    customer = tx_payload.get("customer") or {}
    customer_email = customer.get("email") or tx_payload.get("customer_email")
    metadata = tx_payload.get("metadata") or {}

    seller_id_raw = metadata.get("seller_id")
    coupon_code = metadata.get("coupon_code")

    # 4. Resolve Seller and Coupon details
    seller_id: Optional[UUID] = None
    coupon_id: Optional[UUID] = None
    agreed_discount: Optional[Decimal] = None

    if coupon_code:
        coupon = coupon_service.get_coupon_by_code(coupon_code)
        if coupon:
            if "id" in coupon:
                try:
                    coupon_id = UUID(str(coupon["id"]))
                except ValueError:
                    pass
            if "seller_id" in coupon:
                try:
                    seller_id = UUID(str(coupon["seller_id"]))
                except ValueError:
                    pass
            if coupon.get("agreed_discount") is not None:
                try:
                    agreed_discount = Decimal(str(coupon["agreed_discount"]))
                except Exception:
                    pass

    if not seller_id and seller_id_raw:
        try:
            seller_id = UUID(str(seller_id_raw))
        except ValueError:
            pass

    if seller_id and (agreed_discount is None or coupon_id is None):
        seller = seller_service.get_seller_by_id(seller_id)
        if seller:
            if agreed_discount is None:
                agreed_discount = Decimal(str(seller.agreed_discount))
            if coupon_id is None:
                active_cp = coupon_service.get_active_coupon_for_seller(seller_id)
                if active_cp:
                    coupon_id = active_cp.id

    # Fallback defaults for missing/unconfigured references
    if agreed_discount is None:
        raw_d = metadata.get("agreed_discount")
        agreed_discount = Decimal(str(raw_d)) if raw_d else Decimal("20.00")
    if seller_id is None:
        seller_id = uuid4()
    if coupon_id is None:
        coupon_id = uuid4()

    # 5. Financial recalculations in Ghanaian Cedis (₵)
    quantize_cents = Decimal("0.01")
    amount_paid_ghs = (Decimal(str(amount_pesewas)) / Decimal("100.00")).quantize(
        quantize_cents, rounding=ROUND_HALF_UP
    )
    if amount_paid_ghs <= Decimal("0.00"):
        amount_paid_ghs = Decimal("1.00")

    d = agreed_discount

    # Derive listed_amount from amount_paid: A_listed = A_paid * 200 / (200 - D)
    meta_listed = metadata.get("listed_amount")
    split: Optional[Dict[str, Decimal]] = None
    if meta_listed:
        try:
            candidate_listed = Decimal(str(meta_listed)).quantize(quantize_cents, rounding=ROUND_HALF_UP)
            cand_split = TransactionCreate.calculate_split(candidate_listed, d)
            if abs(cand_split["amount_paid"] - amount_paid_ghs) <= Decimal("0.05"):
                split = cand_split
        except Exception:
            pass

    if not split:
        derived_listed = (amount_paid_ghs * Decimal("200.00") / (Decimal("200.00") - d)).quantize(
            quantize_cents, rounding=ROUND_HALF_UP
        )
        split = TransactionCreate.calculate_split(derived_listed, d)

    listed_amount = split["listed_amount"]
    customer_discount_amount = split["customer_discount_amount"]
    platform_cut_amount = split["customer_discount_amount"]
    actual_amount_paid = amount_paid_ghs
    seller_payout_amount = (actual_amount_paid - platform_cut_amount).quantize(
        quantize_cents, rounding=ROUND_HALF_UP
    )

    # 6. Build and validate TransactionCreate model
    tx_in = TransactionCreate(
        seller_id=seller_id,
        coupon_id=coupon_id,
        paystack_reference=reference,
        currency="GHS",
        listed_amount=listed_amount,
        customer_discount_amount=customer_discount_amount,
        amount_paid=actual_amount_paid,
        platform_cut_amount=platform_cut_amount,
        seller_payout_amount=seller_payout_amount,
        status=target_status,
        customer_email=customer_email,
    )

    # 7. Persist transaction and log event
    try:
        created = create_transaction(tx_in)
        tx_id = created.id if created else None

        log_service.log_event(
            event=raw_event or f"webhook_{target_status.value}",
            transaction_id=tx_id,
            payload=data,
        )

        # Trigger PDF receipt generation and email delivery if customer provided email
        if target_status == TransactionStatus.SUCCESS:
            tx_res_dict = created.model_dump() if created else tx_in.model_dump()
            _send_receipt_if_eligible(
                tx_data=tx_res_dict,
                seller_id=seller_id,
                reference=reference,
                customer_email=customer_email,
                transaction_id=tx_id,
                metadata=metadata,
            )

        return created.model_dump() if created else tx_in.model_dump()
    except Exception as exc:
        logger.error(f"Failed to persist transaction from webhook '{reference}': {exc}")
        log_service.log_event(
            event="webhook_insert_error",
            payload={"error": str(exc), "reference": reference, "raw_data": data},
        )
        return tx_in.model_dump()


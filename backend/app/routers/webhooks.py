import json
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.services import log_service, paystack_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks"])


@router.post(
    "/api/webhooks/paystack",
    summary="Receive Paystack payment webhook events",
    status_code=status.HTTP_200_OK,
)
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Optional[str] = Header(None, alias="x-paystack-signature"),
) -> Dict[str, str]:
    """
    Webhook receiver for Paystack payment lifecycle events.
    - Authenticates via HMAC SHA512 signature in x-paystack-signature header.
    - Handles 'charge.success' and 'charge.failed' events.
    - Idempotent: duplicate webhook deliveries do not create duplicate transactions.
    - Audits every received event payload in transaction_logs.
    - Returns 200 OK with {"status": "ok"}.
    """
    # 1. Read raw body bytes for HMAC signature verification
    raw_body = await request.body()
    if not paystack_service.verify_webhook_signature(raw_body, x_paystack_signature):
        logger.warning("Rejected Paystack webhook: invalid or missing signature.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # 2. Parse JSON payload
    try:
        payload: Dict[str, Any] = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        logger.error(f"Malformed JSON in Paystack webhook: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON body.",
        )

    event = payload.get("event", "")
    data = payload.get("data") or {}
    reference = data.get("reference")

    logger.info(f"Received authentic Paystack webhook event '{event}' (ref: {reference})")

    # 3. Process event & record transaction
    try:
        if event in ("charge.success", "charge.failed"):
            transaction_service.create_transaction_from_webhook(payload)
        else:
            # Audit any other non-charge events sent by Paystack
            log_service.log_event(
                event=f"webhook_{event}" if event else "webhook_unspecified",
                payload=payload,
            )
    except Exception as exc:
        logger.error(f"Unexpected error processing Paystack webhook event '{event}': {exc}", exc_info=True)
        log_service.log_event(
            event="webhook_processing_error",
            payload={"error": str(exc), "event": event, "reference": reference},
        )

    # 4. Immediate 200 OK response to prevent Paystack webhook retries
    return {"status": "ok"}

import logging
from typing import Any, Dict
import resend

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_receipt_email(
    customer_email: str,
    seller_name: str,
    pdf_bytes: bytes,
    reference: str,
) -> Dict[str, Any]:
    """
    Send an official payment receipt PDF to the customer via Resend.

    Parameters:
    - customer_email: Recipient customer email address
    - seller_name: Name of the merchant paid
    - pdf_bytes: Raw in-memory PDF bytes
    - reference: Unique Paystack transaction reference
    """
    settings = get_settings()
    api_key = settings.RESEND_API_KEY
    if not api_key:
        logger.warning(
            f"RESEND_API_KEY is not configured. Simulated email delivery to '{customer_email}' for ref '{reference}'."
        )
        return {"id": "mock_no_api_key", "status": "skipped"}

    resend.api_key = api_key

    from_addr = settings.RESEND_FROM_EMAIL or "onboarding@resend.dev"
    if "<" not in from_addr:
        from_email = f"IncPay <{from_addr}>"
    else:
        from_email = from_addr

    subject = f"Your IncPay Receipt — {seller_name}"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Your IncPay Receipt</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9fafb; margin: 0; padding: 24px;">
  <div style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
    <div style="border-bottom: 1px solid #e5e7eb; padding-bottom: 16px; margin-bottom: 24px;">
      <h1 style="color: #111827; font-size: 22px; font-weight: 800; margin: 0 0 4px 0;">IncPay</h1>
      <p style="color: #6b7280; font-size: 13px; margin: 0;">Payment Confirmation &amp; Official Receipt</p>
    </div>
    
    <p style="color: #374151; font-size: 15px; line-height: 24px; margin: 0 0 16px 0;">
      Thank you for your payment to <strong>{seller_name}</strong>.
    </p>

    <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
      <p style="color: #6b7280; font-size: 12px; font-weight: 600; text-transform: uppercase; margin: 0 0 6px 0;">Transaction Reference</p>
      <p style="color: #111827; font-family: monospace; font-size: 14px; font-weight: 700; margin: 0 0 8px 0;">{reference}</p>
      <p style="color: #059669; font-size: 13px; font-weight: 600; margin: 0;">✓ Payment Completed &amp; Verified</p>
    </div>

    <p style="color: #4b5563; font-size: 14px; line-height: 22px; margin: 0 0 24px 0;">
      Your official receipt with your instant discount breakdown is attached to this email as <strong>receipt-{reference}.pdf</strong>.
    </p>

    <div style="border-top: 1px solid #e5e7eb; padding-top: 16px; font-size: 12px; color: #9ca3af; text-align: center;">
      <p style="margin: 0;">Secured by IncPay • Direct Merchant Split Settlements in Ghanaian Cedis (₵)</p>
    </div>
  </div>
</body>
</html>"""

    # Resend attachment requires list of byte integers or base64
    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": [customer_email],
        "subject": subject,
        "html": html_content,
        "attachments": [
            {
                "filename": f"receipt-{reference}.pdf",
                "content": list(pdf_bytes),
            }
        ],
    }

    try:
        response = resend.Emails.send(params)
        logger.info(f"Successfully dispatched receipt email to {customer_email} for ref {reference}")
        return response
    except Exception as exc:
        logger.error(f"Failed to send receipt email via Resend to {customer_email}: {exc}")
        raise

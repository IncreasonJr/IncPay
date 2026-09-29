import logging
from typing import Any, Dict, Optional
import resend

from app.config import get_settings

from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


def send_receipt_email(
    customer_email: str,
    seller_name: str,
    pdf_bytes: bytes,
    reference: str,
    customer_id: Optional[str] = None,
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

    # Determine customer account call-to-action
    frontend_url = settings.FRONTEND_URL.split(",")[0].strip() or "https://incpay.vercel.app"
    if not customer_id:
        encoded_email = quote_plus(customer_email)
        signup_url = f"{frontend_url.rstrip('/')}/customer/signup?email={encoded_email}"
        account_cta_html = f"""
    <div style="background-color: #f0fdfa; border: 1px solid #ccfbf1; border-radius: 8px; padding: 18px; margin-bottom: 24px; text-align: center;">
      <p style="color: #0f766e; font-size: 14px; font-weight: 700; margin: 0 0 6px 0;">🎉 Create your personal IncPay coupon</p>
      <p style="color: #115e59; font-size: 13px; line-height: 20px; margin: 0 0 14px 0;">
        Track all your receipts, generate your digital loyalty QR card, and view your purchase history in one place.
      </p>
      <a href="{signup_url}" style="display: inline-block; background-color: #0d9488; color: #ffffff; text-decoration: none; font-size: 13px; font-weight: 600; padding: 10px 20px; border-radius: 6px;">
        Claim Your Free Account &amp; Coupon
      </a>
    </div>"""
    else:
        dashboard_url = f"{frontend_url.rstrip('/')}/customer/dashboard"
        account_cta_html = f"""
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 24px; text-align: center;">
      <p style="color: #0f766e; font-size: 13px; font-weight: 600; margin: 0 0 4px 0;">✓ Linked to your IncPay Customer Account</p>
      <p style="color: #64748b; font-size: 12px; margin: 0 0 10px 0;">This transaction has been logged to your dashboard.</p>
      <a href="{dashboard_url}" style="color: #0d9488; font-size: 12px; font-weight: 600; text-decoration: underline;">
        View Customer Dashboard →
      </a>
    </div>"""

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

    <p style="color: #4b5563; font-size: 14px; line-height: 22px; margin: 0 0 20px 0;">
      Your official receipt with your instant discount breakdown is attached to this email as <strong>receipt-{reference}.pdf</strong>.
    </p>

    {account_cta_html}

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

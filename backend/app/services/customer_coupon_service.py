import hashlib
import hmac
import time
from typing import Optional, Dict, Any
from app.config import get_settings


def _get_signing_secret() -> str:
    """Get secret key used for signing customer coupon tokens."""
    settings = get_settings()
    secret = settings.COUPON_SIGNING_SECRET or settings.PAYSTACK_SECRET_KEY or "incpay-coupon-signing-secret"
    return secret


def generate_coupon_token(customer_id: str, timestamp: Optional[int] = None) -> str:
    """
    Generate a tamper-proof cryptographically signed coupon token for a customer.
    Format: {customer_id}.{timestamp}.{signature}
    """
    if timestamp is None:
        timestamp = int(time.time())

    payload = f"{customer_id}.{timestamp}"
    secret = _get_signing_secret().encode("utf-8")
    signature = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    return f"{payload}.{signature}"


def verify_coupon_token(token: str, max_age_seconds: int = 30 * 86400) -> Optional[Dict[str, Any]]:
    """
    Verify the cryptographic signature and freshness of a customer coupon token.
    Enforces a default 30-day expiration window.
    Returns payload dictionary {"customer_id": str, "timestamp": int} if valid, else None.
    """
    if not token or not isinstance(token, str):
        return None

    parts = token.strip().split(".")
    if len(parts) != 3:
        return None

    customer_id, ts_str, signature = parts

    try:
        ts = int(ts_str)
    except ValueError:
        return None

    now = int(time.time())
    # Expiration check (30 days) and prevent far-future timestamps (> 5 min in the future)
    if now - ts > max_age_seconds or ts - now > 300:
        return None

    payload = f"{customer_id}.{ts}"
    secret = _get_signing_secret().encode("utf-8")
    expected_sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if hmac.compare_digest(expected_sig, signature):
        return {"customer_id": customer_id, "timestamp": ts}

    return None


def get_verbal_code(coupon_token: str) -> str:
    """
    Extract a short 8-character verbal verification code from the customer's coupon token.
    Uses the last 8 characters of the cryptographic signature in uppercase.
    """
    if not coupon_token or "." not in coupon_token:
        return "INCPAY00"
    signature_part = coupon_token.split(".")[-1]
    return signature_part[-8:].upper()

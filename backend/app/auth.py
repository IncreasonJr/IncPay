import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_supabase_client

logger = logging.getLogger(__name__)

# auto_error=False allows us to return a consistent 401 with custom error message
security = HTTPBearer(auto_error=False)


def verify_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    FastAPI dependency to verify an incoming Bearer token against Supabase Auth.
    Ensures that the caller is an authenticated user (admin).
    Raises HTTPException(401, "Not authenticated") if token is missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized when validating auth token.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )

    try:
        # Validate JWT and retrieve user from Supabase Auth
        response = client.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired, please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = response.user

        # Strict Role Separation: Ensure this user is NOT a registered customer
        try:
            cust_check = client.table("customers").select("id").eq("supabase_user_id", str(user.id)).execute()
            if cust_check and cust_check.data and len(cust_check.data) > 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Admin privileges required.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.debug(f"Admin customer check exception: {exc}")

        return user
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Failed to authenticate admin token with Supabase: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired, please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_customer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    FastAPI dependency to verify an incoming Bearer token for customer accounts.
    Validates Supabase Auth JWT and ensures a corresponding record exists in 'customers'.
    Raises 401 if missing/invalid token, 403 if user is not a customer or inactive.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )

    try:
        response = client.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired, please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = response.user

        # Query customer profile
        cust_res = client.table("customers").select("*").eq("supabase_user_id", str(user.id)).execute()
        if not cust_res or not cust_res.data or len(cust_res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer account not found.",
            )

        customer = cust_res.data[0]
        if not customer.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer account is inactive. Please contact support.",
            )

        from app.services.customer_coupon_service import get_verbal_code
        customer["verbal_code"] = get_verbal_code(customer.get("coupon_token", ""))
        return customer
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Failed to authenticate customer token: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired, please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_optional_customer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Optional dependency for checkout endpoints.
    Accepts either:
    1. A signed customer coupon token directly.
    2. A valid customer Supabase Auth JWT.
    Returns customer dict if valid, or None if unauthenticated / guest.
    Never raises HTTPException.
    """
    if not credentials or not credentials.credentials:
        return None

    raw_token = credentials.credentials.strip()
    if not raw_token:
        return None

    from app.services.customer_coupon_service import verify_coupon_token, get_verbal_code
    from app.services.customer_service import get_customer_by_id, get_customer_by_supabase_user_id

    # 1. Check if token is a signed coupon token
    token_payload = verify_coupon_token(raw_token)
    if token_payload and "customer_id" in token_payload:
        cust = get_customer_by_id(token_payload["customer_id"])
        if cust and cust.get("is_active", True):
            return cust

    # 2. Check if token is a Supabase Auth JWT
    client = get_supabase_client()
    if client:
        try:
            auth_res = client.auth.get_user(raw_token)
            if auth_res and auth_res.user:
                cust = get_customer_by_supabase_user_id(str(auth_res.user.id))
                if cust and cust.get("is_active", True):
                    return cust
        except Exception:
            pass

    return None


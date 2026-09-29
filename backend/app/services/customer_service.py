import logging
import uuid
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status

from app.database import get_supabase_client
from app.services.customer_coupon_service import generate_coupon_token, get_verbal_code

logger = logging.getLogger(__name__)


def create_customer(
    email: str,
    password: str,
    full_name: str,
    phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Registers a new customer:
    1. Checks if email is already registered in customers table.
    2. Creates Supabase Auth user.
    3. Generates cryptographic coupon token for identity and loyalty tracking.
    4. Inserts record into customers table.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    clean_email = email.strip().lower()

    # 1. Check for duplicate customer email
    try:
        existing = client.table("customers").select("id").eq("email", clean_email).execute()
        if existing and existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please log in.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Error checking existing customer email {clean_email}: {exc}")

    # 2. Create Supabase Auth user
    supabase_user_id = None
    auth_error = None

    # Try admin API first (if service role key is configured)
    try:
        if hasattr(client, "auth") and hasattr(client.auth, "admin") and callable(getattr(client.auth.admin, "create_user", None)):
            admin_res = client.auth.admin.create_user({
                "email": clean_email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": full_name.strip(), "role": "customer"}
            })
            if admin_res and hasattr(admin_res, "user") and admin_res.user:
                supabase_user_id = str(admin_res.user.id)
    except Exception as exc:
        logger.debug(f"Admin create_user not available or failed: {exc}")
        auth_error = str(exc)

    # Fallback to standard sign_up
    if not supabase_user_id:
        try:
            sign_up_res = client.auth.sign_up({
                "email": clean_email,
                "password": password,
                "options": {
                    "data": {"full_name": full_name.strip(), "role": "customer"}
                }
            })
            if sign_up_res and hasattr(sign_up_res, "user") and sign_up_res.user:
                supabase_user_id = str(sign_up_res.user.id)
        except Exception as exc:
            logger.warning(f"Failed to create Supabase Auth user: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to register account: {str(exc)}",
            )

    if not supabase_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create customer user account. Please check your credentials.",
        )

    # 3. Create customer record with cryptographic coupon token
    customer_id = str(uuid.uuid4())
    coupon_token = generate_coupon_token(customer_id)

    customer_payload = {
        "id": customer_id,
        "email": clean_email,
        "full_name": full_name.strip(),
        "phone": phone.strip() if phone else None,
        "supabase_user_id": supabase_user_id,
        "coupon_token": coupon_token,
        "is_active": True,
    }

    try:
        insert_res = client.table("customers").insert(customer_payload).execute()
        if not insert_res or not insert_res.data:
            raise RuntimeError("Database returned empty response after inserting customer")
        customer = insert_res.data[0]
        customer["verbal_code"] = get_verbal_code(coupon_token)
        return customer
    except Exception as exc:
        logger.error(f"Failed to insert customer record: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account created but failed to save profile details. Please contact support.",
        )


def get_customer_by_id(customer_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve customer by internal UUID."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        res = client.table("customers").select("*").eq("id", customer_id).execute()
        if res and res.data and len(res.data) > 0:
            cust = res.data[0]
            cust["verbal_code"] = get_verbal_code(cust.get("coupon_token", ""))
            return cust
    except Exception as exc:
        logger.error(f"Error fetching customer by id {customer_id}: {exc}")
    return None


def get_customer_by_supabase_user_id(supabase_user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve customer by Supabase Auth user ID."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        res = client.table("customers").select("*").eq("supabase_user_id", str(supabase_user_id)).execute()
        if res and res.data and len(res.data) > 0:
            cust = res.data[0]
            cust["verbal_code"] = get_verbal_code(cust.get("coupon_token", ""))
            return cust
    except Exception as exc:
        logger.error(f"Error fetching customer by supabase_user_id {supabase_user_id}: {exc}")
    return None


def get_customer_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve customer by email address."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        clean_email = email.strip().lower()
        res = client.table("customers").select("*").eq("email", clean_email).execute()
        if res and res.data and len(res.data) > 0:
            cust = res.data[0]
            cust["verbal_code"] = get_verbal_code(cust.get("coupon_token", ""))
            return cust
    except Exception as exc:
        logger.error(f"Error fetching customer by email {email}: {exc}")
    return None


def get_customer_transactions(
    customer_id: str,
    page: int = 1,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Fetch paginated transaction history for a specific customer,
    including seller business names.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    safe_page = max(1, page)
    safe_limit = min(max(1, limit), 100)
    offset = (safe_page - 1) * safe_limit

    try:
        # Query transactions joined with seller details
        query = (
            client.table("transactions")
            .select("*, sellers(business_name)", count="exact")
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .range(offset, offset + safe_limit - 1)
        )
        res = query.execute()

        raw_txs = res.data or []
        total = res.count if res.count is not None else len(raw_txs)

        items: List[Dict[str, Any]] = []
        for tx in raw_txs:
            seller_info = tx.get("sellers")
            b_name = "IncPay Merchant"
            if isinstance(seller_info, dict):
                b_name = seller_info.get("business_name") or b_name
            elif isinstance(seller_info, list) and len(seller_info) > 0:
                b_name = seller_info[0].get("business_name") or b_name

            items.append({
                "id": tx.get("id"),
                "created_at": tx.get("created_at"),
                "business_name": b_name,
                "currency": tx.get("currency", "GHS"),
                "listed_amount": tx.get("listed_amount"),
                "customer_discount_amount": tx.get("customer_discount_amount"),
                "amount_paid": tx.get("amount_paid"),
                "paystack_reference": tx.get("paystack_reference"),
                "status": tx.get("status"),
                "receipt_url": f"/api/receipts/{tx.get('paystack_reference')}",
            })

        return {
            "transactions": items,
            "total": total,
            "page": safe_page,
            "limit": safe_limit,
        }
    except Exception as exc:
        logger.error(f"Error fetching customer transactions for {customer_id}: {exc}")
        # Try fallback query without join if foreign table embedding fails
        try:
            query_fallback = (
                client.table("transactions")
                .select("*", count="exact")
                .eq("customer_id", customer_id)
                .order("created_at", desc=True)
                .range(offset, offset + safe_limit - 1)
            )
            res_fb = query_fallback.execute()
            raw_txs = res_fb.data or []
            total = res_fb.count if res_fb.count is not None else len(raw_txs)
            items = []
            for tx in raw_txs:
                items.append({
                    "id": tx.get("id"),
                    "created_at": tx.get("created_at"),
                    "business_name": "IncPay Merchant",
                    "currency": tx.get("currency", "GHS"),
                    "listed_amount": tx.get("listed_amount"),
                    "customer_discount_amount": tx.get("customer_discount_amount"),
                    "amount_paid": tx.get("amount_paid"),
                    "paystack_reference": tx.get("paystack_reference"),
                    "status": tx.get("status"),
                    "receipt_url": f"/api/receipts/{tx.get('paystack_reference')}",
                })
            return {
                "transactions": items,
                "total": total,
                "page": safe_page,
                "limit": safe_limit,
            }
        except Exception as inner_exc:
            logger.error(f"Fallback customer transaction query also failed: {inner_exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve transaction history.",
            )

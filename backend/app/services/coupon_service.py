import logging
from typing import List, Optional, Union
from uuid import UUID

from app.database import get_supabase_client
from app.models.coupon import CouponCreate, CouponResponse

logger = logging.getLogger(__name__)


def create_coupon(coupon_data: CouponCreate) -> Optional[CouponResponse]:
    """
    Generate and persist a new coupon code for a seller.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot create coupon.")
        return None

    try:
        payload = coupon_data.model_dump(mode="json")
        res = client.table("coupons").insert(payload).execute()
        if res.data and len(res.data) > 0:
            return CouponResponse.model_validate(res.data[0])
        logger.warning("No data returned after inserting coupon.")
        return None
    except Exception as exc:
        logger.error(f"Error creating coupon code '{coupon_data.code}': {exc}")
        return None


def get_coupon_by_code(code: str) -> Optional[CouponResponse]:
    """
    Retrieve an active or inactive coupon by its code (case-insensitive lookup).
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot fetch coupon.")
        return None

    try:
        sanitized = code.strip().upper()
        res = client.table("coupons").select("*").eq("code", sanitized).execute()
        if res.data and len(res.data) > 0:
            return CouponResponse.model_validate(res.data[0])
        return None
    except Exception as exc:
        logger.error(f"Error fetching coupon code '{code}': {exc}")
        return None


def list_coupons_for_seller(seller_id: Union[UUID, str]) -> List[CouponResponse]:
    """
    List all coupons associated with a given seller.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot list coupons.")
        return []

    try:
        str_id = str(seller_id)
        res = client.table("coupons").select("*").eq("seller_id", str_id).order("created_at", desc=True).execute()
        if res.data:
            return [CouponResponse.model_validate(row) for row in res.data]
        return []
    except Exception as exc:
        logger.error(f"Error listing coupons for seller id '{seller_id}': {exc}")
        return []


def deactivate_coupon(coupon_id: Union[UUID, str]) -> Optional[CouponResponse]:
    """
    Deactivate a coupon so it can no longer be used for new checkouts.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot deactivate coupon.")
        return None

    try:
        str_id = str(coupon_id)
        res = client.table("coupons").update({"is_active": False}).eq("id", str_id).execute()
        if res.data and len(res.data) > 0:
            return CouponResponse.model_validate(res.data[0])
        logger.warning(f"No coupon found to deactivate with id '{coupon_id}'.")
        return None
    except Exception as exc:
        logger.error(f"Error deactivating coupon id '{coupon_id}': {exc}")
        return None

import logging
import re
import secrets
import string
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.database import get_supabase_client
from app.models.coupon import CouponCreate, CouponResponse

logger = logging.getLogger(__name__)


class CouponDetails(dict):
    """
    Dictionary subclass supporting attribute access (e.g. obj.code)
    and standard dict access (obj['code']).
    """
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'CouponDetails' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def generate_coupon_code(business_name: str) -> str:
    """
    Generate a unique coupon code in the format: {SLUG}-{RANDOM}
    - Slug: first 12 characters of business name, uppercase, alphanumeric only, spaces -> hyphens.
    - Random: 6 uppercase alphanumeric characters.
    - Ensures uniqueness by querying the coupons table (with retry loop).
    """
    # 1. Generate slug
    cleaned_name = re.sub(r"[^A-Za-z0-9\s]+", "", business_name)
    slug_hyphen = re.sub(r"\s+", "-", cleaned_name.strip()).upper()
    slug = slug_hyphen[:12].rstrip("-")
    if not slug:
        slug = "SELLER"

    # 2. Random pool
    chars = string.ascii_uppercase + string.digits

    # 3. Collision check with retry
    client = get_supabase_client()
    for _ in range(10):
        random_suffix = "".join(secrets.choice(chars) for _ in range(6))
        code_candidate = f"{slug}-{random_suffix}"

        if not client:
            return code_candidate

        try:
            res = client.table("coupons").select("id").eq("code", code_candidate).execute()
            if not res.data:
                return code_candidate
        except Exception as exc:
            logger.warning(f"Could not verify coupon uniqueness against database: {exc}")
            return code_candidate

    # Fallback with timestamp-based entropy if all 10 collided
    return f"{slug}-{''.join(secrets.choice(chars) for _ in range(8))}"


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


def create_coupon_for_seller(
    seller_id: Union[UUID, str],
    business_name: str,
) -> Optional[CouponResponse]:
    """
    Generates a unique coupon code and inserts it for the given seller.
    """
    code = generate_coupon_code(business_name)
    coupon_in = CouponCreate(
        seller_id=UUID(str(seller_id)),
        code=code,
        is_active=True,
    )
    return create_coupon(coupon_in)


def get_coupon_by_code(code: str) -> Optional[CouponDetails]:
    """
    Retrieve an active coupon by its code with seller details joined
    (business_name, agreed_discount, seller_id).
    Returns None if not found or inactive.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot fetch coupon.")
        return None

    try:
        sanitized = code.strip().upper()
        # Query coupon
        res = client.table("coupons").select("*").eq("code", sanitized).execute()
        if not res.data or len(res.data) == 0:
            return None

        coupon_row = res.data[0]
        if not coupon_row.get("is_active", True):
            return None

        # Fetch joined seller data
        seller_id = coupon_row.get("seller_id")
        business_name = None
        agreed_discount = None
        subaccount_code = None

        if seller_id:
            try:
                seller_res = client.table("sellers").select("business_name, agreed_discount, paystack_subaccount_code, is_active").eq("id", str(seller_id)).execute()
                if seller_res.data and len(seller_res.data) > 0:
                    s_data = seller_res.data[0]
                    # If seller itself is inactive, reject coupon
                    if s_data.get("is_active") is False:
                        return None
                    business_name = s_data.get("business_name")
                    agreed_discount = s_data.get("agreed_discount")
                    subaccount_code = s_data.get("paystack_subaccount_code")
            except Exception as s_exc:
                logger.warning(f"Failed to fetch joined seller for coupon '{code}': {s_exc}")

        details = dict(coupon_row)
        details["business_name"] = business_name
        details["agreed_discount"] = agreed_discount
        details["paystack_subaccount_code"] = subaccount_code
        return CouponDetails(details)
    except Exception as exc:
        logger.error(f"Error fetching coupon code '{code}': {exc}")
        return None


def get_active_coupon_for_seller(seller_id: Union[UUID, str]) -> Optional[CouponResponse]:
    """
    Retrieve the current active coupon for a seller.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot fetch active coupon.")
        return None

    try:
        str_id = str(seller_id)
        res = (
            client.table("coupons")
            .select("*")
            .eq("seller_id", str_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return CouponResponse.model_validate(res.data[0])
        return None
    except Exception as exc:
        logger.error(f"Error fetching active coupon for seller id '{seller_id}': {exc}")
        return None


def regenerate_coupon_for_seller(
    seller_id: Union[UUID, str],
    business_name: str,
) -> Optional[CouponResponse]:
    """
    Deactivates any existing coupons for this seller, then generates and persists a new coupon.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot regenerate coupon.")
        return None

    str_id = str(seller_id)
    try:
        # 1. Deactivate existing coupons
        client.table("coupons").update({"is_active": False}).eq("seller_id", str_id).execute()
        logger.info(f"Deactivated existing coupons for seller {str_id}.")
    except Exception as exc:
        logger.error(f"Error deactivating old coupons for seller {str_id}: {exc}")

    # 2. Create new active coupon
    return create_coupon_for_seller(seller_id, business_name)


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

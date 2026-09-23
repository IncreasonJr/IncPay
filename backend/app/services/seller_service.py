import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.database import get_supabase_client
from app.models.seller import SellerCreate, SellerResponse, SellerUpdate
from app.services import paystack_service, coupon_service
from app.services.paystack_service import PaystackError

logger = logging.getLogger(__name__)


def calculate_percentage_charge(agreed_discount: Union[Decimal, float]) -> float:
    """
    Calculate IncPay's platform cut percentage on the collected amount.
    Formula: percentage_charge = D / (200 - D) * 100
    Example: D=20% -> 20 / 180 * 100 = 11.11%
    """
    d = float(agreed_discount)
    if d <= 0 or d >= 200:
        raise ValueError("Agreed discount D must be between 0 and 100.")
    return round((d / (200.0 - d)) * 100.0, 2)


def create_seller(seller_data: SellerCreate) -> Optional[SellerResponse]:
    """
    Register a new seller in Supabase and create their Paystack Subaccount.
    If Paystack fails, raises PaystackError so no orphan seller is created.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot create seller.")
        raise RuntimeError("Database client is not available.")

    # 1. Calculate platform percentage charge
    percentage_charge = calculate_percentage_charge(seller_data.agreed_discount)

    # 2. Create Paystack subaccount
    subaccount = paystack_service.create_subaccount(
        business_name=seller_data.business_name,
        settlement_bank=seller_data.settlement_bank_code,
        account_number=seller_data.settlement_account_number,
        percentage_charge=percentage_charge,
        primary_contact_email=str(seller_data.contact_email),
        primary_contact_name=seller_data.settlement_account_name,
        primary_contact_phone=seller_data.contact_phone,
    )

    subaccount_code = subaccount.get("subaccount_code")
    subaccount_id = str(subaccount.get("id", ""))

    # 3. Store seller in Supabase
    payload = seller_data.model_dump(mode="json")
    payload["paystack_subaccount_code"] = subaccount_code
    payload["paystack_subaccount_id"] = subaccount_id

    try:
        res = client.table("sellers").insert(payload).execute()
        if res.data and len(res.data) > 0:
            seller_dict = dict(res.data[0])
            # 4. Automatically generate coupon for onboarded seller
            try:
                coupon = coupon_service.create_coupon_for_seller(
                    seller_id=seller_dict["id"],
                    business_name=seller_data.business_name,
                )
                if coupon:
                    seller_dict["coupon_code"] = coupon.code
            except Exception as c_exc:
                logger.error(f"Failed to generate initial coupon for seller '{seller_data.business_name}': {c_exc}")
            return SellerResponse.model_validate(seller_dict)
        logger.warning("No data returned after inserting seller.")
        return None
    except Exception as exc:
        logger.error(f"Error persisting seller '{seller_data.business_name}' in Supabase: {exc}")
        raise


def get_seller(seller_id: Union[UUID, str]) -> Optional[SellerResponse]:
    """
    Retrieve a seller by their unique UUID, with active coupon attached.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot fetch seller.")
        return None

    try:
        str_id = str(seller_id)
        res = client.table("sellers").select("*").eq("id", str_id).execute()
        if res.data and len(res.data) > 0:
            seller_dict = dict(res.data[0])
            try:
                active_coupon = coupon_service.get_active_coupon_for_seller(str_id)
                if active_coupon:
                    seller_dict["coupon_code"] = active_coupon.code
            except Exception as c_exc:
                logger.warning(f"Could not load active coupon for seller {seller_id}: {c_exc}")
            return SellerResponse.model_validate(seller_dict)
        return None
    except Exception as exc:
        logger.error(f"Error fetching seller id '{seller_id}': {exc}")
        return None


def get_seller_by_id(seller_id: Union[UUID, str]) -> Optional[SellerResponse]:
    """
    Alias for get_seller.
    """
    return get_seller(seller_id)


def list_sellers(
    limit: int = 50,
    offset: int = 0,
    is_active: Optional[bool] = None,
) -> List[SellerResponse]:
    """
    List sellers with optional pagination and active status filtering.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot list sellers.")
        return []

    try:
        query = client.table("sellers").select("*")
        if is_active is not None:
            query = query.eq("is_active", is_active)

        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        if not res.data:
            return []

        # Batch lookup active coupons for list
        coupon_map: Dict[str, str] = {}
        try:
            seller_ids = [str(row["id"]) for row in res.data if "id" in row]
            if seller_ids:
                coupons_res = client.table("coupons").select("seller_id, code").in_("seller_id", seller_ids).eq("is_active", True).execute()
                if coupons_res.data:
                    for c_row in coupons_res.data:
                        coupon_map[str(c_row["seller_id"])] = c_row["code"]
        except Exception as c_exc:
            logger.warning(f"Could not batch fetch coupons for sellers list: {c_exc}")

        results = []
        for row in res.data:
            s_dict = dict(row)
            s_dict["coupon_code"] = coupon_map.get(str(s_dict.get("id")))
            results.append(SellerResponse.model_validate(s_dict))
        return results
    except Exception as exc:
        logger.error(f"Error listing sellers: {exc}")
        return []


def update_seller(
    seller_id: Union[UUID, str],
    update_data: SellerUpdate,
) -> Optional[SellerResponse]:
    """
    Update seller attributes.
    If agreed_discount changes, updates the Paystack subaccount percentage_charge as well.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot update seller.")
        return None

    existing = get_seller(seller_id)
    if not existing:
        logger.warning(f"Seller not found for id '{seller_id}'.")
        return None

    # Check if agreed_discount changed and update Paystack subaccount
    if (
        update_data.agreed_discount is not None
        and update_data.agreed_discount != existing.agreed_discount
        and existing.paystack_subaccount_code
    ):
        new_charge = calculate_percentage_charge(update_data.agreed_discount)
        try:
            paystack_service.update_subaccount(
                subaccount_code=existing.paystack_subaccount_code,
                percentage_charge=new_charge,
            )
            logger.info(
                f"Updated Paystack subaccount {existing.paystack_subaccount_code} "
                f"percentage_charge to {new_charge}%"
            )
        except Exception as exc:
            logger.error(f"Failed to update Paystack subaccount charge: {exc}")
            raise

    payload = update_data.model_dump(exclude_unset=True, mode="json")
    if not payload:
        return existing

    try:
        str_id = str(seller_id)
        res = client.table("sellers").update(payload).eq("id", str_id).execute()
        if res.data and len(res.data) > 0:
            return SellerResponse.model_validate(res.data[0])
        return None
    except Exception as exc:
        logger.error(f"Error updating seller id '{seller_id}': {exc}")
        raise


def delete_seller(seller_id: Union[UUID, str]) -> bool:
    """
    Delete a seller from Supabase.
    Associated coupons will be deleted by CASCADE foreign key constraint.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot delete seller.")
        return False

    try:
        str_id = str(seller_id)
        res = client.table("sellers").delete().eq("id", str_id).execute()
        if res.data and len(res.data) > 0:
            return True
        return False
    except Exception as exc:
        logger.error(f"Error deleting seller id '{seller_id}': {exc}")
        return False


def list_banks(currency: str = "GHS") -> List[Dict[str, Any]]:
    """Proxy to paystack_service.list_banks."""
    return paystack_service.list_banks(currency=currency)


def list_mobile_money_providers(currency: str = "GHS") -> List[Dict[str, str]]:
    """Proxy to paystack_service.list_mobile_money_providers."""
    return paystack_service.list_mobile_money_providers(currency=currency)

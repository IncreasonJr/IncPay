import logging
from typing import List, Optional, Union
from uuid import UUID

from app.database import get_supabase_client
from app.models.seller import SellerCreate, SellerResponse, SellerUpdate

logger = logging.getLogger(__name__)


def create_seller(seller_data: SellerCreate) -> Optional[SellerResponse]:
    """
    Register a new seller in Supabase.
    agreed_discount (D) is stored as numeric in Cedis/percentage context.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot create seller.")
        return None

    try:
        # Convert Decimal and UUID to JSON-compatible types
        payload = seller_data.model_dump(mode="json")
        res = client.table("sellers").insert(payload).execute()
        if res.data and len(res.data) > 0:
            return SellerResponse.model_validate(res.data[0])
        logger.warning("No data returned after inserting seller.")
        return None
    except Exception as exc:
        logger.error(f"Error creating seller '{seller_data.business_name}': {exc}")
        return None


def get_seller(seller_id: Union[UUID, str]) -> Optional[SellerResponse]:
    """
    Retrieve a seller by their unique UUID.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot fetch seller.")
        return None

    try:
        str_id = str(seller_id)
        res = client.table("sellers").select("*").eq("id", str_id).execute()
        if res.data and len(res.data) > 0:
            return SellerResponse.model_validate(res.data[0])
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
        if res.data:
            return [SellerResponse.model_validate(row) for row in res.data]
        return []
    except Exception as exc:
        logger.error(f"Error listing sellers: {exc}")
        return []


def update_seller(
    seller_id: Union[UUID, str],
    update_data: SellerUpdate,
) -> Optional[SellerResponse]:
    """
    Update seller attributes. Only provided (non-None) fields are updated.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot update seller.")
        return None

    payload = update_data.model_dump(exclude_unset=True, mode="json")
    if not payload:
        # Nothing to update, return current record
        return get_seller(seller_id)

    try:
        str_id = str(seller_id)
        res = client.table("sellers").update(payload).eq("id", str_id).execute()
        if res.data and len(res.data) > 0:
            return SellerResponse.model_validate(res.data[0])
        logger.warning(f"No seller found or updated for id '{seller_id}'.")
        return None
    except Exception as exc:
        logger.error(f"Error updating seller id '{seller_id}': {exc}")
        return None


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
        logger.warning(f"No seller deleted for id '{seller_id}'.")
        return False
    except Exception as exc:
        logger.error(f"Error deleting seller id '{seller_id}': {exc}")
        return False

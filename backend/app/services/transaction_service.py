import logging
from typing import List, Optional, Union
from uuid import UUID

from app.database import get_supabase_client
from app.models.transaction import TransactionCreate, TransactionResponse, TransactionStatus

logger = logging.getLogger(__name__)


def create_transaction(tx_data: TransactionCreate) -> Optional[TransactionResponse]:
    """
    Record a new payment-bridge transaction in Supabase.
    Amounts are stored in Ghanaian Cedis (numeric/Decimal).
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot create transaction.")
        return None

    try:
        # Decimal values are serialized to float/string or numeric representations for json
        payload = tx_data.model_dump(mode="json")
        res = client.table("transactions").insert(payload).execute()
        if res.data and len(res.data) > 0:
            return TransactionResponse.model_validate(res.data[0])
        logger.warning(f"No transaction returned after inserting reference '{tx_data.paystack_reference}'.")
        return None
    except Exception as exc:
        logger.error(f"Error creating transaction '{tx_data.paystack_reference}': {exc}")
        return None


def get_transaction_by_reference(reference: str) -> Optional[TransactionResponse]:
    """
    Retrieve a transaction record by its unique Paystack payment reference.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot fetch transaction.")
        return None

    try:
        res = client.table("transactions").select("*").eq("paystack_reference", reference).execute()
        if res.data and len(res.data) > 0:
            return TransactionResponse.model_validate(res.data[0])
        return None
    except Exception as exc:
        logger.error(f"Error fetching transaction reference '{reference}': {exc}")
        return None


def list_transactions(
    seller_id: Optional[Union[UUID, str]] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[TransactionResponse]:
    """
    List transactions, optionally filtered by seller ID, ordered by creation date descending.
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot list transactions.")
        return []

    try:
        query = client.table("transactions").select("*")
        if seller_id is not None:
            query = query.eq("seller_id", str(seller_id))

        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        if res.data:
            return [TransactionResponse.model_validate(row) for row in res.data]
        return []
    except Exception as exc:
        logger.error(f"Error listing transactions: {exc}")
        return []


def update_transaction_status(
    reference: str,
    status: Union[TransactionStatus, str],
) -> Optional[TransactionResponse]:
    """
    Update the status of a transaction (e.g., pending -> success or failed).
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot update transaction status.")
        return None

    try:
        status_value = status.value if isinstance(status, TransactionStatus) else str(status)
        res = client.table("transactions").update({"status": status_value}).eq("paystack_reference", reference).execute()
        if res.data and len(res.data) > 0:
            return TransactionResponse.model_validate(res.data[0])
        logger.warning(f"No transaction found or updated for reference '{reference}'.")
        return None
    except Exception as exc:
        logger.error(f"Error updating transaction status for reference '{reference}': {exc}")
        return None

import logging
from typing import Any, Dict, Optional, Union
from uuid import UUID

from app.database import get_supabase_client
from app.models.log import LogCreate, LogResponse

logger = logging.getLogger(__name__)


def log_event(
    event: Union[LogCreate, str],
    transaction_id: Optional[Union[UUID, str]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[LogResponse]:
    """
    Record a transaction audit log event into the transaction_logs table.
    Accepts either a LogCreate model or individual parameters (event_type, transaction_id, payload).
    """
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client not initialized. Cannot record transaction log.")
        return None

    if isinstance(event, LogCreate):
        log_create = event
    else:
        log_create = LogCreate(
            event_type=event,
            transaction_id=UUID(str(transaction_id)) if transaction_id else None,
            payload=payload,
        )

    try:
        data = log_create.model_dump(mode="json")
        res = client.table("transaction_logs").insert(data).execute()
        if res.data and len(res.data) > 0:
            return LogResponse.model_validate(res.data[0])
        logger.warning(f"No log response returned after inserting event '{log_create.event_type}'.")
        return None
    except Exception as exc:
        logger.error(f"Error recording log event '{log_create.event_type}': {exc}")
        return None

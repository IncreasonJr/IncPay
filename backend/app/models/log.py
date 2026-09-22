from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class LogCreate(BaseModel):
    """Payload for creating a transaction audit log entry."""
    transaction_id: Optional[UUID] = Field(None, description="Related transaction ID if applicable")
    event_type: str = Field(..., min_length=1, description="Event name (e.g. payment_initiated, webhook_received)")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Raw JSON data associated with the event")


class LogResponse(LogCreate):
    """Schema returned for transaction audit log records."""
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

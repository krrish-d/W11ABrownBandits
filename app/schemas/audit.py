from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    audit_id: str
    entity_type: str
    entity_id: str
    action: str
    changed_by: Optional[str]
    changes: Optional[str]      # raw JSON string; parse client-side if needed
    timestamp: datetime

    class Config:
        from_attributes = True

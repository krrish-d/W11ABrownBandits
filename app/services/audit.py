import json
from typing import Optional
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_audit(
    db: Session,
    entity_type: str,
    entity_id: str,
    action: str,
    changed_by: Optional[str] = "system",
    changes: Optional[dict] = None,
) -> None:
    """
    Append an audit entry.  The caller is responsible for committing the session
    (so this can be batched with the main write in a single transaction).
    """
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by=changed_by or "system",
        changes=json.dumps(changes) if changes else None,
    )
    db.add(entry)

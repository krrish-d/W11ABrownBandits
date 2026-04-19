from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=list[AuditLogResponse])
def get_audit_logs(
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type, e.g. 'invoice'"),
    entity_id: Optional[str] = Query(default=None, description="Filter by specific entity ID"),
    action: Optional[str] = Query(default=None, description="Filter by action, e.g. 'update'"),
    changed_by: Optional[str] = Query(default=None, description="Filter by user_id or 'system'"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Returns the audit trail, ordered newest-first.
    """
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if changed_by:
        q = q.filter(AuditLog.changed_by == changed_by)

    return (
        q.order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[AuditLogResponse])
def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
):
    """Full history for a single entity."""
    return (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )

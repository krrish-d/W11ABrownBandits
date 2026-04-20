from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.recurring import RecurringInvoice
from app.models.template import InvoiceTemplate
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.services.auth import get_optional_current_user, user_owns_record

router = APIRouter(prefix="/audit", tags=["Audit Log"])


def _owned_entity_ids_for_user(
    db: Session,
    current_user: Optional[User],
) -> dict[str, set[str]]:
    """
    Return a mapping of entity_type -> set of entity_ids that the caller
    is allowed to see audit rows for.  Uses the same owner-scoping rule
    that applies everywhere else (authenticated users see their rows,
    anonymous callers see unowned rows).
    """
    owner_id = current_user.user_id if current_user else None

    def _scope(model, id_column):
        q = db.query(id_column)
        if current_user is not None:
            q = q.filter(model.owner_id == owner_id)
        else:
            q = q.filter(model.owner_id.is_(None))
        return {row[0] for row in q.all()}

    mapping: dict[str, set[str]] = {
        "invoice":   _scope(Invoice, Invoice.invoice_id),
        "client":    _scope(Client, Client.client_id),
        "recurring": _scope(RecurringInvoice, RecurringInvoice.recurring_id),
        "template":  _scope(InvoiceTemplate, InvoiceTemplate.template_id),
    }
    if current_user is not None:
        # Users can always see audit rows for their own user record
        mapping["user"] = {current_user.user_id}

    # Also include payments by joining to owned invoices
    from app.models.payment import Payment

    payment_q = (
        db.query(Payment.payment_id)
        .join(Invoice, Invoice.invoice_id == Payment.invoice_id)
    )
    if current_user is not None:
        payment_q = payment_q.filter(Invoice.owner_id == owner_id)
    else:
        payment_q = payment_q.filter(Invoice.owner_id.is_(None))
    mapping["payment"] = {row[0] for row in payment_q.all()}

    return mapping


def _apply_ownership_filter(
    db: Session,
    q,
    current_user: Optional[User],
):
    """
    Restrict an AuditLog query to rows the caller is allowed to see.

    A row is visible if:
      (a) it was changed_by the caller directly, OR
      (b) its (entity_type, entity_id) pair references a record the caller
          owns per the standard scoping rule.
    """
    owned = _owned_entity_ids_for_user(db, current_user)

    entity_filters = []
    for entity_type, ids in owned.items():
        if ids:
            entity_filters.append(
                (AuditLog.entity_type == entity_type)
                & AuditLog.entity_id.in_(ids)
            )

    conditions = []
    if current_user is not None:
        conditions.append(AuditLog.changed_by == current_user.user_id)
    if entity_filters:
        conditions.append(or_(*entity_filters))

    if not conditions:
        # Anonymous caller with nothing owned: hide everything.
        return q.filter(False)
    return q.filter(or_(*conditions))


@router.get("", response_model=list[AuditLogResponse])
def get_audit_logs(
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type, e.g. 'invoice'"),
    entity_id: Optional[str] = Query(default=None, description="Filter by specific entity ID"),
    action: Optional[str] = Query(default=None, description="Filter by action, e.g. 'update'"),
    changed_by: Optional[str] = Query(default=None, description="Filter by user_id or 'system'"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns the audit trail, ordered newest-first, scoped to the caller's
    own records and actions.
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

    q = _apply_ownership_filter(db, q, current_user)

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
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Full history for a single entity. Only visible to the owner."""
    owner_id: Optional[str] = None
    if entity_type == "invoice":
        row = db.query(Invoice.owner_id).filter(Invoice.invoice_id == entity_id).first()
        owner_id = row[0] if row else None
    elif entity_type == "client":
        row = db.query(Client.owner_id).filter(Client.client_id == entity_id).first()
        owner_id = row[0] if row else None
    elif entity_type == "recurring":
        row = (
            db.query(RecurringInvoice.owner_id)
            .filter(RecurringInvoice.recurring_id == entity_id)
            .first()
        )
        owner_id = row[0] if row else None
    elif entity_type == "template":
        row = (
            db.query(InvoiceTemplate.owner_id)
            .filter(InvoiceTemplate.template_id == entity_id)
            .first()
        )
        owner_id = row[0] if row else None
    elif entity_type == "payment":
        from app.models.payment import Payment
        row = (
            db.query(Invoice.owner_id)
            .join(Payment, Payment.invoice_id == Invoice.invoice_id)
            .filter(Payment.payment_id == entity_id)
            .first()
        )
        owner_id = row[0] if row else None
    elif entity_type == "user":
        if current_user is None or current_user.user_id != entity_id:
            raise HTTPException(status_code=404, detail="Audit trail not found")
        owner_id = entity_id
    else:
        # Unknown entity type - deny for safety
        raise HTTPException(status_code=404, detail="Audit trail not found")

    if entity_type != "user" and not user_owns_record(current_user, owner_id):
        raise HTTPException(status_code=404, detail="Audit trail not found")

    return (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )

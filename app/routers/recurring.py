import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.recurring import RecurringInvoice
from app.models.user import User
from app.schemas.invoice import InvoiceCreate
from app.schemas.recurring import (
    RecurringInvoiceCreate,
    RecurringInvoiceUpdate,
    RecurringInvoiceResponse,
    VALID_FREQUENCIES,
)
from app.services.audit import log_audit
from app.services.auth import get_optional_current_user, scope_query_to_owner, user_owns_record
from app.services.scheduler import generate_recurring_invoices

router = APIRouter(prefix="/recurring", tags=["Recurring Invoices"])


def _validate_frequency(frequency: str) -> None:
    if frequency not in VALID_FREQUENCIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid frequency '{frequency}'. Must be one of: {', '.join(sorted(VALID_FREQUENCIES))}",
        )


# -------------------------------------------------------
# POST /recurring
# -------------------------------------------------------
@router.post("", response_model=RecurringInvoiceResponse, status_code=201)
def create_recurring(
    payload: RecurringInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    _validate_frequency(payload.frequency)

    # Validate that invoice_template is a valid InvoiceCreate payload
    try:
        InvoiceCreate(**payload.invoice_template)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid invoice_template: {e}")

    rule = RecurringInvoice(
        owner_id=current_user.user_id if current_user else None,
        name=payload.name,
        frequency=payload.frequency,
        next_run_date=payload.next_run_date,
        end_date=payload.end_date,
        invoice_template=json.dumps(payload.invoice_template),
    )
    db.add(rule)
    # Flush so SQLAlchemy assigns recurring_id before we reference it in the audit log
    db.flush()
    log_audit(db, "recurring", rule.recurring_id, "create",
              changed_by=current_user.user_id if current_user else None)
    db.commit()
    db.refresh(rule)
    return rule


# -------------------------------------------------------
# GET /recurring
# -------------------------------------------------------
@router.get("", response_model=list[RecurringInvoiceResponse])
def list_recurring(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    q = scope_query_to_owner(
        db.query(RecurringInvoice), RecurringInvoice.owner_id, current_user
    )
    return q.order_by(RecurringInvoice.next_run_date).all()


# -------------------------------------------------------
# GET /recurring/{recurring_id}
# -------------------------------------------------------
@router.get("/{recurring_id}", response_model=RecurringInvoiceResponse)
def get_recurring(
    recurring_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    rule = db.query(RecurringInvoice).filter(RecurringInvoice.recurring_id == recurring_id).first()
    if not rule or not user_owns_record(current_user, rule.owner_id):
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    return rule


# -------------------------------------------------------
# PUT /recurring/{recurring_id}
# -------------------------------------------------------
@router.put("/{recurring_id}", response_model=RecurringInvoiceResponse)
def update_recurring(
    recurring_id: str,
    payload: RecurringInvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    rule = db.query(RecurringInvoice).filter(RecurringInvoice.recurring_id == recurring_id).first()
    if not rule or not user_owns_record(current_user, rule.owner_id):
        raise HTTPException(status_code=404, detail="Recurring rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "frequency" in update_data:
        _validate_frequency(update_data["frequency"])
    if "invoice_template" in update_data:
        try:
            InvoiceCreate(**update_data["invoice_template"])
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid invoice_template: {e}")
        update_data["invoice_template"] = json.dumps(update_data["invoice_template"])

    for field, value in update_data.items():
        setattr(rule, field, value)

    log_audit(db, "recurring", recurring_id, "update",
              changed_by=current_user.user_id if current_user else None)
    db.commit()
    db.refresh(rule)
    return rule


# -------------------------------------------------------
# DELETE /recurring/{recurring_id}
# -------------------------------------------------------
@router.delete("/{recurring_id}", status_code=200)
def delete_recurring(
    recurring_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    rule = db.query(RecurringInvoice).filter(RecurringInvoice.recurring_id == recurring_id).first()
    if not rule or not user_owns_record(current_user, rule.owner_id):
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    log_audit(db, "recurring", recurring_id, "delete",
              changed_by=current_user.user_id if current_user else None)
    db.delete(rule)
    db.commit()
    return {"message": f"Recurring rule {recurring_id} deleted"}


# -------------------------------------------------------
# POST /recurring/trigger  (manual run – admin / dev tool)
# -------------------------------------------------------
@router.post("/trigger", status_code=202)
def trigger_recurring_job():
    """Manually fire the recurring invoice generation job (useful for testing)."""
    generate_recurring_invoices()
    return {"message": "Recurring invoice generation triggered"}

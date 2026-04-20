from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse, InvoicePaymentSummary
from app.services.audit import log_audit
from app.services.auth import get_optional_current_user, user_owns_record

router = APIRouter(prefix="/payments", tags=["Payment Tracking"])


def _get_owned_invoice_or_404(
    db: Session,
    invoice_id: str,
    current_user: Optional[User],
) -> Invoice:
    """Load an invoice and ensure it belongs to the caller's scope."""
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice or not user_owns_record(current_user, invoice.owner_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


def _get_owned_payment_or_404(
    db: Session,
    payment_id: str,
    current_user: Optional[User],
) -> Payment:
    """Load a payment and ensure its parent invoice belongs to the caller."""
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    invoice = db.query(Invoice).filter(Invoice.invoice_id == payment.invoice_id).first()
    if not invoice or not user_owns_record(current_user, invoice.owner_id):
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


def _refresh_invoice_status(invoice: Invoice, db: Session) -> None:
    """Auto-set invoice status to 'paid' when total payments cover the grand total."""
    total_paid = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.invoice_id == invoice.invoice_id)
        .scalar()
        or 0.0
    )
    if total_paid >= invoice.grand_total and invoice.status not in ("cancelled",):
        invoice.status = "paid"


# -------------------------------------------------------
# POST /payments
# -------------------------------------------------------
@router.post("", response_model=PaymentResponse, status_code=201)
def record_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    invoice = _get_owned_invoice_or_404(db, payload.invoice_id, current_user)

    payment = Payment(**payload.model_dump())
    db.add(payment)
    db.flush()

    _refresh_invoice_status(invoice, db)
    log_audit(db, "payment", payment.payment_id, "create",
              changed_by=current_user.user_id if current_user else None,
              changes={"invoice_id": payload.invoice_id, "amount": payload.amount})
    db.commit()
    db.refresh(payment)
    return payment


# -------------------------------------------------------
# GET /payments  (all payments)
# -------------------------------------------------------
@router.get("", response_model=list[PaymentResponse])
def list_payments(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    owner_id = current_user.user_id if current_user else None
    q = (
        db.query(Payment)
        .join(Invoice, Invoice.invoice_id == Payment.invoice_id)
    )
    if current_user is not None:
        q = q.filter(Invoice.owner_id == owner_id)
    else:
        q = q.filter(Invoice.owner_id.is_(None))
    return q.order_by(Payment.payment_date.desc()).all()


# -------------------------------------------------------
# GET /payments/invoice/{invoice_id}  – per-invoice summary
# -------------------------------------------------------
@router.get("/invoice/{invoice_id}", response_model=InvoicePaymentSummary)
def get_invoice_payment_summary(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    invoice = _get_owned_invoice_or_404(db, invoice_id, current_user)

    payments = (
        db.query(Payment)
        .filter(Payment.invoice_id == invoice_id)
        .order_by(Payment.payment_date)
        .all()
    )
    total_paid = round(sum(p.amount for p in payments), 2)
    outstanding = round(invoice.grand_total - total_paid, 2)

    return InvoicePaymentSummary(
        invoice_id=invoice_id,
        grand_total=invoice.grand_total,
        total_paid=total_paid,
        outstanding_balance=max(outstanding, 0.0),
        payments=[PaymentResponse.model_validate(p) for p in payments],
    )


# -------------------------------------------------------
# GET /payments/{payment_id}
# -------------------------------------------------------
@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    return _get_owned_payment_or_404(db, payment_id, current_user)


# -------------------------------------------------------
# PUT /payments/{payment_id}
# -------------------------------------------------------
@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: str,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    payment = _get_owned_payment_or_404(db, payment_id, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment, field, value)

    invoice = db.query(Invoice).filter(Invoice.invoice_id == payment.invoice_id).first()
    if invoice:
        _refresh_invoice_status(invoice, db)

    log_audit(db, "payment", payment_id, "update",
              changed_by=current_user.user_id if current_user else None)
    db.commit()
    db.refresh(payment)
    return payment


# -------------------------------------------------------
# DELETE /payments/{payment_id}
# -------------------------------------------------------
@router.delete("/{payment_id}", status_code=200)
def delete_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    payment = _get_owned_payment_or_404(db, payment_id, current_user)

    invoice_id = payment.invoice_id
    log_audit(db, "payment", payment_id, "delete",
              changed_by=current_user.user_id if current_user else None)
    db.delete(payment)
    db.flush()

    # Re-evaluate invoice status after payment removal
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if invoice and invoice.status == "paid":
        total_paid = (
            db.query(func.sum(Payment.amount))
            .filter(Payment.invoice_id == invoice_id)
            .scalar()
            or 0.0
        )
        if total_paid < invoice.grand_total:
            invoice.status = "sent"

    db.commit()
    return {"message": f"Payment {payment_id} deleted successfully"}

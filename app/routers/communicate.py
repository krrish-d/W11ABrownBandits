import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.communication import CommunicationLog
from app.models.invoice import Invoice, LineItem
from app.models.invoice_import import InvoiceImportToken
from app.models.user import User
from app.schemas.communication import (
    CommunicationRequest,
    CommunicationLogResponse,
    CommunicationSendResponse,
)
from app.services.auth import get_optional_current_user, user_owns_record
from app.services.communicate import (
    send_invoice_email,
    send_invoice_with_import_link,
    send_payment_reminder,
)


def _get_owned_invoice_or_404(
    db: Session,
    invoice_id: str,
    current_user: Optional[User],
) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice or not user_owns_record(current_user, invoice.owner_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

router = APIRouter(
    prefix="/communicate",
    tags=["Invoice Communication"]
)


# -------------------------------------------------------
# POST /communicate/send — Send UBL XML invoice by email (original)
# -------------------------------------------------------
@router.post("/send", response_model=CommunicationSendResponse)
def send_invoice(request: CommunicationRequest, db: Session = Depends(get_db)):
    try:
        delivery_confirmation = send_invoice_email(
            invoice_xml=request.invoice_xml,
            recipient_email=request.recipient_email
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    log = CommunicationLog(
        invoice_id=delivery_confirmation["invoice_id"],
        recipient_email=delivery_confirmation["recipient_email"],
        delivery_status=delivery_confirmation["status"]
    )
    db.add(log)
    db.commit()

    return delivery_confirmation


# -------------------------------------------------------
# POST /communicate/send-invoice/{invoice_id}
#   Send a rich HTML email with an "Add to My Library" import button.
# -------------------------------------------------------
@router.post("/send-invoice/{invoice_id}", status_code=200)
def send_invoice_with_link(
    invoice_id: str,
    recipient_email: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Fetches the invoice from the database, generates a one-time signed import
    token, sends a styled HTML email to *recipient_email* that contains an
    'Add to My Invoice Library' button, and logs the communication.

    The import token is valid for 7 days and can only be used once.
    """
    invoice = _get_owned_invoice_or_404(db, invoice_id, current_user)

    items = db.query(LineItem).filter(LineItem.invoice_id == invoice_id).all()

    # Generate and persist the import token
    token_value = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    import_token = InvoiceImportToken(
        invoice_id=invoice_id,
        token=token_value,
        expires_at=expires_at,
    )
    db.add(import_token)
    db.flush()  # get token_id persisted before sending

    try:
        result = send_invoice_with_import_link(
            invoice=invoice,
            items=items,
            recipient_email=recipient_email,
            import_token=token_value,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    # Update invoice status to "sent"
    if invoice.status == "draft":
        invoice.status = "sent"

    log = CommunicationLog(
        invoice_id=invoice_id,
        recipient_email=recipient_email,
        delivery_status="sent",
    )
    db.add(log)
    db.commit()

    return {
        "message": "Invoice email sent successfully",
        "invoice_id": invoice_id,
        "recipient_email": recipient_email,
        "import_url": result.get("import_url"),
        "token_expires_at": expires_at.isoformat(),
    }


# -------------------------------------------------------
# POST /communicate/remind/{invoice_id}
#   Manually send a payment reminder for an overdue/unpaid invoice.
# -------------------------------------------------------
@router.post("/remind/{invoice_id}", status_code=200)
def send_reminder(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    invoice = _get_owned_invoice_or_404(db, invoice_id, current_user)
    if not invoice.buyer_email:
        raise HTTPException(status_code=422, detail="Invoice has no buyer email")

    try:
        send_payment_reminder(invoice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    log = CommunicationLog(
        invoice_id=invoice_id,
        recipient_email=invoice.buyer_email,
        delivery_status="reminder",
    )
    db.add(log)
    db.commit()

    return {"message": "Payment reminder sent", "invoice_id": invoice_id, "recipient": invoice.buyer_email}


# -------------------------------------------------------
# GET /communicate/logs — List all sent invoice logs
# -------------------------------------------------------
@router.get("/logs", response_model=list[CommunicationLogResponse])
def get_communication_logs(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns communication logs for invoices owned by the caller. Logs that
    reference invoices outside the caller's scope (e.g. raw-XML sends via
    /communicate/send with no matching DB row) are always hidden.
    """
    q = db.query(CommunicationLog).join(
        Invoice, Invoice.invoice_id == CommunicationLog.invoice_id
    )
    if current_user is not None:
        q = q.filter(Invoice.owner_id == current_user.user_id)
    else:
        q = q.filter(Invoice.owner_id.is_(None))
    return q.order_by(CommunicationLog.sent_at.desc()).all()


# -------------------------------------------------------
# GET /communicate/health — Communication service health
# -------------------------------------------------------
@router.get("/health")
def communication_health_check():
    return {
        "status": "healthy",
        "service": "Invoice Communication"
    }

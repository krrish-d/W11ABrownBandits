from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.communication import CommunicationLog
from app.schemas.communication import (
    CommunicationRequest,
    CommunicationLogResponse,
    CommunicationSendResponse,
)
from app.services.communicate import send_invoice_email

router = APIRouter(
    prefix="/communicate",
    tags=["Invoice Communication"]
)


# -------------------------------------------------------
# POST /communicate/send — Send UBL XML invoice by email
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
# GET /communicate/logs — List all sent invoice logs
# -------------------------------------------------------
@router.get("/logs", response_model=list[CommunicationLogResponse])
def get_communication_logs(db: Session = Depends(get_db)):
    return db.query(CommunicationLog).order_by(CommunicationLog.sent_at.desc()).all()


# -------------------------------------------------------
# GET /communicate/health — Communication service health
# -------------------------------------------------------
@router.get("/health")
def communication_health_check():
    return {
        "status": "healthy",
        "service": "Invoice Communication"
    }

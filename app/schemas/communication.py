from datetime import datetime
from pydantic import BaseModel


class CommunicationRequest(BaseModel):
    invoice_xml: str
    recipient_email: str


class CommunicationSendResponse(BaseModel):
    status: str
    timestamp: datetime
    recipient_email: str
    invoice_id: str


class CommunicationLogResponse(BaseModel):
    log_id: str
    invoice_id: str
    recipient_email: str
    delivery_status: str
    sent_at: datetime

    class Config:
        from_attributes = True

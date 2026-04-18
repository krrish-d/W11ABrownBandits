import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    log_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    delivery_status = Column(String, default="sent", nullable=False)
    sent_at = Column(DateTime, server_default=func.now(), nullable=False)

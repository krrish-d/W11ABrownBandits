import uuid
from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.invoice_id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    # bank_transfer | credit_card | cash | xero | other
    method = Column(String, nullable=False, default="bank_transfer")
    reference = Column(String, nullable=True)    # payment reference / transaction ID
    payment_date = Column(Date, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    invoice = relationship("Invoice", backref="payments")

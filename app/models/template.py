import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class InvoiceTemplate(Base):
    __tablename__ = "invoice_templates"

    template_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    primary_colour = Column(String, default="#2563eb", nullable=False)
    secondary_colour = Column(String, default="#1e40af", nullable=False)
    footer_text = Column(String, nullable=True)
    payment_terms_text = Column(String, nullable=True)
    bank_details = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

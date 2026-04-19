import uuid
from sqlalchemy import Column, String, Boolean, Date, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class RecurringInvoice(Base):
    __tablename__ = "recurring_invoices"

    recurring_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, nullable=True)
    # Human-readable label, e.g. "Monthly retainer – Acme Corp"
    name = Column(String, nullable=False)
    # daily | weekly | biweekly | monthly | quarterly | annually
    frequency = Column(String, nullable=False)
    next_run_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)          # None = run forever
    is_active = Column(Boolean, default=True, nullable=False)
    # Serialised InvoiceCreate payload (JSON)
    invoice_template = Column(Text, nullable=False)
    last_run_date = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

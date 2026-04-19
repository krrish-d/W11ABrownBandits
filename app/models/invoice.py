import uuid
from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_number = Column(String, unique=True, nullable=False)
    # draft | sent | viewed | paid | overdue | cancelled
    status = Column(String, default="draft")
    # Optional: user who owns/created this invoice
    owner_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    # Optional: template used when generating PDFs
    template_id = Column(String, ForeignKey("invoice_templates.template_id", ondelete="SET NULL"), nullable=True)
    seller_name = Column(String, nullable=False)
    seller_address = Column(String, nullable=False)
    seller_email = Column(String, nullable=False)
    buyer_name = Column(String, nullable=False)
    buyer_address = Column(String, nullable=False)
    buyer_email = Column(String, nullable=False)
    client_name = Column(String, nullable=False)
    client_email = Column(String, nullable=False)
    currency = Column(String, default="AUD")
    due_date = Column(Date, nullable=False)
    notes = Column(String, nullable=True)
    subtotal = Column(Float, default=0.0)
    tax_total = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship("LineItem", back_populates="invoice", cascade="all, delete")

class LineItem(Base):
    __tablename__ = "line_items"

    item_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.invoice_id"), nullable=False)
    item_number = Column(String, nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    tax_rate = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")

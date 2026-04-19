import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class InvoiceImportToken(Base):
    """
    One-time token embedded in the 'Add to My Library' email link.
    When the recipient follows the link the backend creates a copy of the
    invoice in their library and marks this token as used.
    """
    __tablename__ = "invoice_import_tokens"

    token_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.invoice_id", ondelete="CASCADE"), nullable=False)
    # URL-safe random token – stored and matched on GET /invoice/import/{token}
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    # user_id of the account that claimed the invoice (None if anonymous)
    imported_by = Column(String, nullable=True)

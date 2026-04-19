import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    client_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Nullable so unregistered users can still create clients
    owner_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    address = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)          # ABN / GST / VAT number
    currency = Column(String, default="AUD", nullable=False)
    payment_terms = Column(Integer, default=30)     # days until due
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

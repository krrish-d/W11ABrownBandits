import uuid
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # e.g. "invoice" | "client" | "payment" | "recurring" | "template" | "user"
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    # "create" | "update" | "delete" | "status_change" | "email_sent" | "imported"
    action = Column(String, nullable=False)
    # user_id who triggered the change, or "system" for scheduled jobs
    changed_by = Column(String, nullable=True, default="system")
    # JSON: {"field": {"old": <value>, "new": <value>}, ...}
    changes = Column(Text, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

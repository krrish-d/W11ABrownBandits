from datetime import date, datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel

VALID_FREQUENCIES = {"daily", "weekly", "biweekly", "monthly", "quarterly", "annually"}


class RecurringInvoiceCreate(BaseModel):
    name: str
    frequency: str                          # must be one of VALID_FREQUENCIES
    next_run_date: date
    end_date: Optional[date] = None
    # Full InvoiceCreate payload – validated at creation time
    invoice_template: Dict[str, Any]


class RecurringInvoiceUpdate(BaseModel):
    name: Optional[str] = None
    frequency: Optional[str] = None
    next_run_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    invoice_template: Optional[Dict[str, Any]] = None


class RecurringInvoiceResponse(BaseModel):
    recurring_id: str
    owner_id: Optional[str]
    name: str
    frequency: str
    next_run_date: date
    end_date: Optional[date]
    is_active: bool
    last_run_date: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True

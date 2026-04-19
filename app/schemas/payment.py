from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float = Field(gt=0)
    method: str = "bank_transfer"   # bank_transfer | credit_card | cash | xero | other
    reference: Optional[str] = None
    payment_date: date
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    method: Optional[str] = None
    reference: Optional[str] = None
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: str
    invoice_id: str
    amount: float
    method: str
    reference: Optional[str]
    payment_date: date
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class InvoicePaymentSummary(BaseModel):
    invoice_id: str
    grand_total: float
    total_paid: float
    outstanding_balance: float
    payments: list[PaymentResponse]

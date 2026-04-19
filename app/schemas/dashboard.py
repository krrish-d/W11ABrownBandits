from typing import Dict, List, Optional
from pydantic import BaseModel


class StatusCounts(BaseModel):
    draft: int = 0
    sent: int = 0
    viewed: int = 0
    paid: int = 0
    overdue: int = 0
    cancelled: int = 0


class KPIResponse(BaseModel):
    total_invoiced_all_time: float
    paid_this_month: float
    overdue_amount: float
    outstanding_balance: float      # invoiced but not yet paid (all time)
    avg_days_to_payment: Optional[float]
    invoice_counts: StatusCounts
    total_invoices: int


class MonthlyDataPoint(BaseModel):
    month: str                      # "YYYY-MM"
    invoiced: float
    paid: float
    overdue: float


class TrendResponse(BaseModel):
    monthly: List[MonthlyDataPoint]


class AttentionInvoice(BaseModel):
    invoice_id: str
    invoice_number: str
    buyer_name: str
    grand_total: float
    currency: str
    due_date: str
    status: str
    days_overdue: Optional[int]
    days_until_due: Optional[int]


class NeedsAttentionResponse(BaseModel):
    overdue: List[AttentionInvoice]
    due_within_7_days: List[AttentionInvoice]


class TopClientEntry(BaseModel):
    buyer_name: str
    total_invoiced: float
    total_paid: float
    outstanding: float
    invoice_count: int


class TopClientsResponse(BaseModel):
    top_clients: List[TopClientEntry]

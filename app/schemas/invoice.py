from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class LineItemCreate(BaseModel):
    description: str
    quantity: float
    unit_price: float
    tax_rate: float

class LineItemResponse(LineItemCreate):
    item_id: str
    line_total: float

    class Config:
        from_attributes = True

class InvoiceCreate(BaseModel):
    client_name: str
    client_email: str
    currency: str = "AUD"
    due_date: date
    notes: Optional[str] = None
    items: List[LineItemCreate]

class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    currency: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None

class InvoiceResponse(BaseModel):
    invoice_id: str
    invoice_number: str
    status: str
    client_name: str
    client_email: str
    currency: str
    due_date: date
    notes: Optional[str]
    subtotal: float
    tax_total: float
    grand_total: float
    items: List[LineItemResponse]

    class Config:
        from_attributes = True

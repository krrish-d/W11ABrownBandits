from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class LineItemCreate(BaseModel):
    item_number: str
    description: str
    quantity: float
    unit_price: float
    tax_rate: float = 0.0

class LineItemResponse(LineItemCreate):
    item_id: str
    line_total: float

    class Config:
        from_attributes = True

class InvoiceCreate(BaseModel):
    seller_name: str
    seller_address: str
    seller_email: str
    buyer_name: str
    buyer_address: str
    buyer_email: str
    currency: str = "AUD"
    due_date: date
    notes: Optional[str] = None
    items: List[LineItemCreate] = Field(min_length=1)

class InvoiceUpdate(BaseModel):
    seller_name: Optional[str] = None
    seller_address: Optional[str] = None
    seller_email: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_email: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    currency: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None

class InvoiceResponse(BaseModel):
    invoice_id: str
    invoice_number: str
    status: str
    seller_name: str
    seller_address: str
    seller_email: str
    buyer_name: str
    buyer_address: str
    buyer_email: str
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

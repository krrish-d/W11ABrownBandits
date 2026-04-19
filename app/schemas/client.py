from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    email: str
    address: Optional[str] = None
    tax_id: Optional[str] = None
    currency: str = "AUD"
    payment_terms: int = 30
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    currency: Optional[str] = None
    payment_terms: Optional[int] = None
    notes: Optional[str] = None


class ClientResponse(BaseModel):
    client_id: str
    owner_id: Optional[str]
    name: str
    email: str
    address: Optional[str]
    tax_id: Optional[str]
    currency: str
    payment_terms: int
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    logo_url: Optional[str] = None
    primary_colour: str = "#2563eb"
    secondary_colour: str = "#1e40af"
    footer_text: Optional[str] = None
    payment_terms_text: Optional[str] = None
    bank_details: Optional[str] = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_colour: Optional[str] = None
    secondary_colour: Optional[str] = None
    footer_text: Optional[str] = None
    payment_terms_text: Optional[str] = None
    bank_details: Optional[str] = None
    is_default: Optional[bool] = None


class TemplateResponse(BaseModel):
    template_id: str
    owner_id: Optional[str]
    name: str
    logo_url: Optional[str]
    primary_colour: str
    secondary_colour: str
    footer_text: Optional[str]
    payment_terms_text: Optional[str]
    bank_details: Optional[str]
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True

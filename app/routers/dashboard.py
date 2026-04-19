from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import (
    KPIResponse,
    TrendResponse,
    NeedsAttentionResponse,
    TopClientsResponse,
)
from app.services.dashboard import (
    get_kpis,
    get_monthly_trend,
    get_needs_attention,
    get_top_clients,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/kpis", response_model=KPIResponse)
def dashboard_kpis(db: Session = Depends(get_db)):
    """
    Key performance indicators:
    - Total invoiced (all time)
    - Amount paid this calendar month
    - Current overdue amount
    - Outstanding balance (unpaid)
    - Average days to payment
    - Invoice counts by status
    """
    return get_kpis(db)


@router.get("/trend", response_model=TrendResponse)
def dashboard_trend(
    months: int = Query(default=12, ge=1, le=36, description="How many months of history to return"),
    db: Session = Depends(get_db),
):
    """Monthly breakdown of invoiced vs paid vs overdue amounts."""
    return get_monthly_trend(db, months=months)


@router.get("/needs-attention", response_model=NeedsAttentionResponse)
def dashboard_needs_attention(db: Session = Depends(get_db)):
    """
    Returns:
    - Overdue invoices
    - Invoices due within the next 7 days
    """
    return get_needs_attention(db)


@router.get("/top-clients", response_model=TopClientsResponse)
def dashboard_top_clients(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top clients ranked by total invoiced amount with outstanding balance."""
    return get_top_clients(db, limit=limit)

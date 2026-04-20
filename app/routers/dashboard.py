from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import (
    KPIResponse,
    TrendResponse,
    NeedsAttentionResponse,
    TopClientsResponse,
)
from app.services.auth import get_optional_current_user
from app.services.dashboard import (
    get_kpis,
    get_monthly_trend,
    get_needs_attention,
    get_top_clients,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/kpis", response_model=KPIResponse)
def dashboard_kpis(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Key performance indicators, scoped to the caller's own invoices.
    """
    return get_kpis(db, current_user=current_user)


@router.get("/trend", response_model=TrendResponse)
def dashboard_trend(
    months: int = Query(default=12, ge=1, le=36, description="How many months of history to return"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Monthly breakdown of invoiced vs paid vs overdue amounts for the caller."""
    return get_monthly_trend(db, months=months, current_user=current_user)


@router.get("/needs-attention", response_model=NeedsAttentionResponse)
def dashboard_needs_attention(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns (scoped to the caller):
    - Overdue invoices
    - Invoices due within the next 7 days
    """
    return get_needs_attention(db, current_user=current_user)


@router.get("/top-clients", response_model=TopClientsResponse)
def dashboard_top_clients(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Top clients ranked by total invoiced amount for the caller."""
    return get_top_clients(db, limit=limit, current_user=current_user)

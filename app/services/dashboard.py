from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.user import User
from app.schemas.dashboard import (
    KPIResponse,
    StatusCounts,
    MonthlyDataPoint,
    TrendResponse,
    NeedsAttentionResponse,
    AttentionInvoice,
    TopClientEntry,
    TopClientsResponse,
)
from app.services.auth import scope_query_to_owner


def _scoped_invoice_query(db: Session, current_user: Optional[User]):
    return scope_query_to_owner(db.query(Invoice), Invoice.owner_id, current_user)


def _scoped_payment_query(db: Session, current_user: Optional[User]):
    """
    Payments don't carry an owner column directly, so restrict to payments
    whose parent invoice is owned by the caller.
    """
    q = db.query(Payment).join(Invoice, Invoice.invoice_id == Payment.invoice_id)
    if current_user is not None:
        return q.filter(Invoice.owner_id == current_user.user_id)
    return q.filter(Invoice.owner_id.is_(None))


# -------------------------------------------------------
# KPI cards
# -------------------------------------------------------

def get_kpis(db: Session, current_user: Optional[User] = None) -> KPIResponse:
    today = date.today()
    month_start = today.replace(day=1)

    total_invoiced = (
        _scoped_invoice_query(db, current_user)
        .with_entities(func.sum(Invoice.grand_total))
        .scalar()
        or 0.0
    )

    # Sum of payments recorded this calendar month (scoped to caller's invoices)
    paid_this_month = (
        _scoped_payment_query(db, current_user)
        .filter(Payment.payment_date >= month_start)
        .with_entities(func.sum(Payment.amount))
        .scalar()
        or 0.0
    )

    overdue_amount = (
        _scoped_invoice_query(db, current_user)
        .filter(Invoice.status == "overdue")
        .with_entities(func.sum(Invoice.grand_total))
        .scalar()
        or 0.0
    )

    total_payments_ever = (
        _scoped_payment_query(db, current_user)
        .with_entities(func.sum(Payment.amount))
        .scalar()
        or 0.0
    )
    outstanding_balance = round(total_invoiced - total_payments_ever, 2)

    # Average days to payment: difference between invoice created_at and first payment
    avg_days: Optional[float] = None
    owned_invoices = _scoped_invoice_query(db, current_user).subquery()
    rows = (
        db.query(owned_invoices.c.created_at, func.min(Payment.payment_date))
        .join(Payment, Payment.invoice_id == owned_invoices.c.invoice_id)
        .filter(owned_invoices.c.status == "paid")
        .group_by(owned_invoices.c.invoice_id, owned_invoices.c.created_at)
        .all()
    )
    if rows:
        deltas = [
            (r[1] - r[0].date()).days
            for r in rows
            if r[0] and r[1]
        ]
        if deltas:
            avg_days = round(sum(deltas) / len(deltas), 1)

    # Status counts
    raw_counts = (
        _scoped_invoice_query(db, current_user)
        .with_entities(Invoice.status, func.count(Invoice.invoice_id))
        .group_by(Invoice.status)
        .all()
    )
    count_map = {s: c for s, c in raw_counts}
    counts = StatusCounts(
        draft=count_map.get("draft", 0),
        sent=count_map.get("sent", 0),
        viewed=count_map.get("viewed", 0),
        paid=count_map.get("paid", 0),
        overdue=count_map.get("overdue", 0),
        cancelled=count_map.get("cancelled", 0),
    )
    total_invoices = (
        _scoped_invoice_query(db, current_user)
        .with_entities(func.count(Invoice.invoice_id))
        .scalar()
        or 0
    )

    return KPIResponse(
        total_invoiced_all_time=round(total_invoiced, 2),
        paid_this_month=round(paid_this_month, 2),
        overdue_amount=round(overdue_amount, 2),
        outstanding_balance=outstanding_balance,
        avg_days_to_payment=avg_days,
        invoice_counts=counts,
        total_invoices=total_invoices,
    )


# -------------------------------------------------------
# Monthly revenue trend (last N months)
# -------------------------------------------------------

def get_monthly_trend(
    db: Session,
    months: int = 12,
    current_user: Optional[User] = None,
) -> TrendResponse:
    today = date.today()
    data: List[MonthlyDataPoint] = []

    for i in range(months - 1, -1, -1):
        # Walk backwards month by month
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = f"{year}-{month:02d}"
        m_start = date(year, month, 1)
        # First day of the *next* month used as exclusive upper bound so that
        # timestamps on the last day of the month are not cut off at midnight.
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        m_next = date(next_year, next_month, 1)

        invoiced = (
            _scoped_invoice_query(db, current_user)
            .filter(Invoice.created_at >= m_start, Invoice.created_at < m_next)
            .with_entities(func.sum(Invoice.grand_total))
            .scalar()
            or 0.0
        )
        paid = (
            _scoped_payment_query(db, current_user)
            .filter(Payment.payment_date >= m_start, Payment.payment_date < m_next)
            .with_entities(func.sum(Payment.amount))
            .scalar()
            or 0.0
        )
        overdue = (
            _scoped_invoice_query(db, current_user)
            .filter(
                Invoice.status == "overdue",
                Invoice.due_date >= m_start,
                Invoice.due_date < m_next,
            )
            .with_entities(func.sum(Invoice.grand_total))
            .scalar()
            or 0.0
        )
        data.append(MonthlyDataPoint(
            month=label,
            invoiced=round(invoiced, 2),
            paid=round(paid, 2),
            overdue=round(overdue, 2),
        ))

    return TrendResponse(monthly=data)


# -------------------------------------------------------
# Needs attention panel
# -------------------------------------------------------

def get_needs_attention(
    db: Session,
    current_user: Optional[User] = None,
) -> NeedsAttentionResponse:
    today = date.today()
    soon = today + timedelta(days=7)

    overdue_invoices = (
        _scoped_invoice_query(db, current_user)
        .filter(Invoice.status == "overdue")
        .order_by(Invoice.due_date)
        .limit(50)
        .all()
    )

    soon_due = (
        _scoped_invoice_query(db, current_user)
        .filter(
            Invoice.due_date > today,
            Invoice.due_date <= soon,
            Invoice.status.notin_(["paid", "cancelled"]),
        )
        .order_by(Invoice.due_date)
        .limit(50)
        .all()
    )

    def _to_attention(inv: Invoice, *, is_overdue: bool) -> AttentionInvoice:
        days_overdue = (today - inv.due_date).days if is_overdue else None
        days_until = (inv.due_date - today).days if not is_overdue else None
        return AttentionInvoice(
            invoice_id=inv.invoice_id,
            invoice_number=inv.invoice_number,
            buyer_name=inv.buyer_name,
            grand_total=inv.grand_total,
            currency=inv.currency,
            due_date=str(inv.due_date),
            status=inv.status,
            days_overdue=days_overdue,
            days_until_due=days_until,
        )

    return NeedsAttentionResponse(
        overdue=[_to_attention(i, is_overdue=True) for i in overdue_invoices],
        due_within_7_days=[_to_attention(i, is_overdue=False) for i in soon_due],
    )


# -------------------------------------------------------
# Top clients
# -------------------------------------------------------

def get_top_clients(
    db: Session,
    limit: int = 10,
    current_user: Optional[User] = None,
) -> TopClientsResponse:
    rows = (
        _scoped_invoice_query(db, current_user)
        .with_entities(
            Invoice.buyer_name,
            func.sum(Invoice.grand_total).label("total_invoiced"),
            func.count(Invoice.invoice_id).label("invoice_count"),
        )
        .group_by(Invoice.buyer_name)
        .order_by(func.sum(Invoice.grand_total).desc())
        .limit(limit)
        .all()
    )

    entries = []
    for buyer_name, total_invoiced, invoice_count in rows:
        # Sum payments for this buyer's invoices within the caller's scope
        invoice_ids = [
            r.invoice_id
            for r in _scoped_invoice_query(db, current_user)
            .with_entities(Invoice.invoice_id)
            .filter(Invoice.buyer_name == buyer_name)
            .all()
        ]
        total_paid = (
            db.query(func.sum(Payment.amount))
            .filter(Payment.invoice_id.in_(invoice_ids))
            .scalar()
            or 0.0
        )
        entries.append(TopClientEntry(
            buyer_name=buyer_name,
            total_invoiced=round(total_invoiced or 0.0, 2),
            total_paid=round(total_paid, 2),
            outstanding=round((total_invoiced or 0.0) - total_paid, 2),
            invoice_count=invoice_count,
        ))

    return TopClientsResponse(top_clients=entries)

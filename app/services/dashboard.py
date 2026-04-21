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
    """
    Build the monthly bar chart with a fixed number of database round-trips.

    Previous implementation ran 3 queries per month (36 queries for the
    default 12 month window), which turned into 15-20s page loads on a
    remote DB. The aggregates are now computed with one GROUP BY query
    per series, then zipped with the expected month labels in Python.
    """
    today = date.today()

    # Build the ordered list of (label, year, month) buckets we want to return.
    buckets: List[tuple[str, int, int]] = []
    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        buckets.append((f"{year}-{month:02d}", year, month))

    window_start_year, window_start_month = buckets[0][1], buckets[0][2]
    window_start = date(window_start_year, window_start_month, 1)

    def _bucket_aggregate(query, date_column, value_column):
        """Run a single GROUP BY year/month query and return a {label: value} map."""
        year_expr = func.extract("year", date_column)
        month_expr = func.extract("month", date_column)
        rows = (
            query
            .with_entities(year_expr, month_expr, func.sum(value_column))
            .filter(date_column >= window_start)
            .group_by(year_expr, month_expr)
            .all()
        )
        out: dict[str, float] = {}
        for y, m, total in rows:
            if y is None or m is None:
                continue
            label = f"{int(y)}-{int(m):02d}"
            out[label] = float(total or 0.0)
        return out

    invoiced_map = _bucket_aggregate(
        _scoped_invoice_query(db, current_user),
        Invoice.created_at,
        Invoice.grand_total,
    )
    paid_map = _bucket_aggregate(
        _scoped_payment_query(db, current_user),
        Payment.payment_date,
        Payment.amount,
    )
    overdue_map = _bucket_aggregate(
        _scoped_invoice_query(db, current_user).filter(Invoice.status == "overdue"),
        Invoice.due_date,
        Invoice.grand_total,
    )

    data = [
        MonthlyDataPoint(
            month=label,
            invoiced=round(invoiced_map.get(label, 0.0), 2),
            paid=round(paid_map.get(label, 0.0), 2),
            overdue=round(overdue_map.get(label, 0.0), 2),
        )
        for label, _, _ in buckets
    ]

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
    """
    Return the top-N buyers by total invoiced amount.

    Previous implementation ran one extra payments query per client in the
    result set. This version uses two aggregate queries total: one to pick
    the top buyers, one to sum payments across their invoices.
    """
    top_rows = (
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

    buyer_names = [row[0] for row in top_rows if row[0] is not None]

    paid_map: dict[str, float] = {}
    if buyer_names:
        paid_rows = (
            _scoped_payment_query(db, current_user)
            .with_entities(Invoice.buyer_name, func.sum(Payment.amount))
            .filter(Invoice.buyer_name.in_(buyer_names))
            .group_by(Invoice.buyer_name)
            .all()
        )
        paid_map = {bn: float(amt or 0.0) for bn, amt in paid_rows}

    entries = [
        TopClientEntry(
            buyer_name=buyer_name,
            total_invoiced=round(total_invoiced or 0.0, 2),
            total_paid=round(paid_map.get(buyer_name, 0.0), 2),
            outstanding=round(
                (total_invoiced or 0.0) - paid_map.get(buyer_name, 0.0), 2
            ),
            invoice_count=invoice_count,
        )
        for buyer_name, total_invoiced, invoice_count in top_rows
    ]

    return TopClientsResponse(top_clients=entries)

"""Unit tests for app.services.dashboard against an isolated sqlite DB."""

import os
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.invoice import Invoice, LineItem
from app.models.payment import Payment
from app.services.dashboard import (
    get_kpis,
    get_monthly_trend,
    get_needs_attention,
    get_top_clients,
)


TEST_DB_PATH = "./test_dashboard_unit.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture
def db_session():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)


def _make_invoice(
    db,
    *,
    invoice_number: str,
    grand_total: float,
    status: str = "sent",
    due_date: date = None,
    buyer_name: str = "Acme Corp",
):
    inv = Invoice(
        invoice_number=invoice_number,
        owner_id=None,
        seller_name="Seller",
        seller_address="addr",
        seller_email="seller@example.com",
        buyer_name=buyer_name,
        buyer_address="addr",
        buyer_email="buyer@example.com",
        client_name=buyer_name,
        client_email="buyer@example.com",
        currency="AUD",
        due_date=due_date or date.today() + timedelta(days=10),
        subtotal=grand_total / 1.1,
        tax_total=grand_total - (grand_total / 1.1),
        grand_total=grand_total,
        status=status,
    )
    db.add(inv)
    db.flush()
    db.add(LineItem(
        invoice_id=inv.invoice_id,
        item_number="1",
        description="Item",
        quantity=1,
        unit_price=grand_total,
        tax_rate=0,
        line_total=grand_total,
    ))
    return inv


def _make_payment(db, invoice_id: str, amount: float, when: date = None):
    db.add(Payment(
        invoice_id=invoice_id,
        amount=amount,
        method="bank_transfer",
        payment_date=when or date.today(),
    ))


# -------------------------------------------------------
# KPIs
# -------------------------------------------------------

def test_kpis_empty_db_returns_zeros(db_session):
    kpis = get_kpis(db_session)
    assert kpis.total_invoiced_all_time == 0.0
    assert kpis.paid_this_month == 0.0
    assert kpis.overdue_amount == 0.0
    assert kpis.outstanding_balance == 0.0
    assert kpis.total_invoices == 0
    assert kpis.invoice_counts.draft == 0


def test_kpis_with_invoices_and_payments(db_session):
    inv1 = _make_invoice(db_session, invoice_number="INV-1", grand_total=1000.0, status="sent")
    inv2 = _make_invoice(db_session, invoice_number="INV-2", grand_total=500.0, status="paid")
    _make_invoice(
        db_session,
        invoice_number="INV-3",
        grand_total=300.0,
        status="overdue",
        due_date=date.today() - timedelta(days=5),
    )
    db_session.commit()

    _make_payment(db_session, inv1.invoice_id, 200.0)
    _make_payment(db_session, inv2.invoice_id, 500.0)
    db_session.commit()

    kpis = get_kpis(db_session)
    assert kpis.total_invoices == 3
    assert kpis.total_invoiced_all_time == 1800.0
    assert kpis.paid_this_month == 700.0
    assert kpis.overdue_amount == 300.0
    assert kpis.outstanding_balance == 1100.0
    assert kpis.invoice_counts.sent == 1
    assert kpis.invoice_counts.paid == 1
    assert kpis.invoice_counts.overdue == 1


# -------------------------------------------------------
# Trend
# -------------------------------------------------------

def test_trend_returns_requested_months(db_session):
    trend = get_monthly_trend(db_session, months=12)
    assert len(trend.monthly) == 12


def test_trend_three_months(db_session):
    trend = get_monthly_trend(db_session, months=3)
    assert len(trend.monthly) == 3


def test_trend_includes_invoice_amount_in_current_month(db_session):
    _make_invoice(db_session, invoice_number="INV-T", grand_total=500.0)
    db_session.commit()

    trend = get_monthly_trend(db_session, months=1)
    assert trend.monthly[0].invoiced == 500.0


# -------------------------------------------------------
# Needs attention
# -------------------------------------------------------

def test_needs_attention_lists_overdue(db_session):
    _make_invoice(
        db_session,
        invoice_number="INV-OD",
        grand_total=100.0,
        status="overdue",
        due_date=date.today() - timedelta(days=3),
    )
    db_session.commit()

    needs = get_needs_attention(db_session)
    assert len(needs.overdue) == 1
    assert needs.overdue[0].days_overdue == 3


def test_needs_attention_lists_due_within_7_days(db_session):
    _make_invoice(
        db_session,
        invoice_number="INV-SOON",
        grand_total=100.0,
        status="sent",
        due_date=date.today() + timedelta(days=3),
    )
    db_session.commit()

    needs = get_needs_attention(db_session)
    assert len(needs.due_within_7_days) == 1
    assert needs.due_within_7_days[0].days_until_due == 3


def test_needs_attention_excludes_paid_and_cancelled(db_session):
    _make_invoice(
        db_session,
        invoice_number="INV-PAID",
        grand_total=100.0,
        status="paid",
        due_date=date.today() + timedelta(days=2),
    )
    _make_invoice(
        db_session,
        invoice_number="INV-CXL",
        grand_total=100.0,
        status="cancelled",
        due_date=date.today() + timedelta(days=2),
    )
    db_session.commit()

    needs = get_needs_attention(db_session)
    assert needs.due_within_7_days == []


# -------------------------------------------------------
# Top clients
# -------------------------------------------------------

def test_top_clients_ranks_by_total_invoiced(db_session):
    _make_invoice(db_session, invoice_number="A1", grand_total=1000.0, buyer_name="Alpha Co")
    _make_invoice(db_session, invoice_number="A2", grand_total=500.0, buyer_name="Alpha Co")
    _make_invoice(db_session, invoice_number="B1", grand_total=300.0, buyer_name="Beta Co")
    db_session.commit()

    res = get_top_clients(db_session, limit=10)
    assert len(res.top_clients) == 2
    assert res.top_clients[0].buyer_name == "Alpha Co"
    assert res.top_clients[0].total_invoiced == 1500.0
    assert res.top_clients[0].invoice_count == 2
    assert res.top_clients[1].buyer_name == "Beta Co"


def test_top_clients_outstanding_subtracts_payments(db_session):
    inv = _make_invoice(db_session, invoice_number="A1", grand_total=1000.0, buyer_name="Alpha Co")
    db_session.commit()
    _make_payment(db_session, inv.invoice_id, 400.0)
    db_session.commit()

    res = get_top_clients(db_session, limit=10)
    assert res.top_clients[0].total_paid == 400.0
    assert res.top_clients[0].outstanding == 600.0


def test_top_clients_respects_limit(db_session):
    for i in range(5):
        _make_invoice(
            db_session,
            invoice_number=f"INV-{i}",
            grand_total=100.0 + i,
            buyer_name=f"Buyer {i}",
        )
    db_session.commit()

    res = get_top_clients(db_session, limit=2)
    assert len(res.top_clients) == 2

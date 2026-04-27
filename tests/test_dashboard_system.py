"""System tests for /dashboard/* endpoints."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app


TEST_DB_PATH = "./test_dashboard_system.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="module", autouse=True)
def isolated_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


client = TestClient(app)


def _create_invoice(buyer_name: str = "Buyer Co", grand_total_target: float = 1100.0):
    """Helper that posts a 1-line invoice (qty 2 × 500 + 10% GST = 1100 by default)."""
    res = client.post(
        "/invoice/create",
        json={
            "seller_name": "Seller Co",
            "seller_address": "1 Seller St",
            "seller_email": "seller@example.com",
            "buyer_name": buyer_name,
            "buyer_address": "2 Buyer Rd",
            "buyer_email": f"{uuid.uuid4().hex[:6]}@example.com",
            "currency": "AUD",
            "due_date": "2026-12-31",
            "items": [
                {
                    "item_number": "1",
                    "description": "Widget",
                    "quantity": 2,
                    "unit_price": 500.0,
                    "tax_rate": 10.0,
                }
            ],
        },
    )
    assert res.status_code == 201
    return res.json()


# -------------------------------------------------------
# /dashboard/kpis
# -------------------------------------------------------

def test_kpis_returns_expected_shape():
    res = client.get("/dashboard/kpis")
    assert res.status_code == 200
    body = res.json()
    for key in [
        "total_invoiced_all_time",
        "paid_this_month",
        "overdue_amount",
        "outstanding_balance",
        "avg_days_to_payment",
        "invoice_counts",
        "total_invoices",
    ]:
        assert key in body
    for status_key in ["draft", "sent", "viewed", "paid", "overdue", "cancelled"]:
        assert status_key in body["invoice_counts"]


def test_kpis_includes_created_invoice():
    initial = client.get("/dashboard/kpis").json()
    _create_invoice()
    after = client.get("/dashboard/kpis").json()
    assert after["total_invoices"] == initial["total_invoices"] + 1


# -------------------------------------------------------
# /dashboard/trend
# -------------------------------------------------------

def test_trend_default_returns_12_months():
    res = client.get("/dashboard/trend")
    assert res.status_code == 200
    assert len(res.json()["monthly"]) == 12


def test_trend_custom_months():
    res = client.get("/dashboard/trend?months=6")
    assert res.status_code == 200
    assert len(res.json()["monthly"]) == 6


def test_trend_rejects_zero_months():
    res = client.get("/dashboard/trend?months=0")
    assert res.status_code == 422


def test_trend_rejects_too_many_months():
    res = client.get("/dashboard/trend?months=100")
    assert res.status_code == 422


# -------------------------------------------------------
# /dashboard/needs-attention
# -------------------------------------------------------

def test_needs_attention_returns_expected_shape():
    res = client.get("/dashboard/needs-attention")
    assert res.status_code == 200
    body = res.json()
    assert "overdue" in body
    assert "due_within_7_days" in body
    assert isinstance(body["overdue"], list)
    assert isinstance(body["due_within_7_days"], list)


# -------------------------------------------------------
# /dashboard/top-clients
# -------------------------------------------------------

def test_top_clients_returns_list():
    res = client.get("/dashboard/top-clients")
    assert res.status_code == 200
    assert "top_clients" in res.json()
    assert isinstance(res.json()["top_clients"], list)


def test_top_clients_respects_limit():
    for name in ("Alpha", "Beta", "Gamma"):
        _create_invoice(buyer_name=name)
    res = client.get("/dashboard/top-clients?limit=2")
    assert res.status_code == 200
    assert len(res.json()["top_clients"]) <= 2


def test_top_clients_rejects_invalid_limit():
    res = client.get("/dashboard/top-clients?limit=0")
    assert res.status_code == 422

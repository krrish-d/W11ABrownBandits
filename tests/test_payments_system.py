"""System tests for /payments/* endpoints."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app


TEST_DB_PATH = "./test_payments_system.db"
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


def _invoice_payload(buyer_email: str = "buyer@example.com", grand_total_target: float = 1100.0):
    """A simple 1-line invoice with grand_total = 1100 (qty 2 × 500 + 10% GST)."""
    return {
        "seller_name": "Seller Co",
        "seller_address": "1 Seller St",
        "seller_email": "seller@example.com",
        "buyer_name": "Buyer Co",
        "buyer_address": "2 Buyer Rd",
        "buyer_email": buyer_email,
        "currency": "AUD",
        "due_date": "2026-06-01",
        "items": [
            {
                "item_number": "1",
                "description": "Widget",
                "quantity": 2,
                "unit_price": 500.0,
                "tax_rate": 10.0,
            }
        ],
    }


def _create_invoice(buyer_email: str = None) -> dict:
    if buyer_email is None:
        buyer_email = f"buyer-{uuid.uuid4().hex[:6]}@example.com"
    res = client.post("/invoice/create", json=_invoice_payload(buyer_email=buyer_email))
    assert res.status_code == 201
    return res.json()


# -------------------------------------------------------
# Record payment
# -------------------------------------------------------

def test_record_payment_success():
    invoice = _create_invoice()
    res = client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": 100.0,
            "method": "bank_transfer",
            "payment_date": "2026-04-20",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["payment_id"]
    assert body["amount"] == 100.0
    assert body["method"] == "bank_transfer"


def test_record_payment_missing_invoice_returns_404():
    res = client.post(
        "/payments",
        json={
            "invoice_id": "no-such-invoice",
            "amount": 100.0,
            "method": "bank_transfer",
            "payment_date": "2026-04-20",
        },
    )
    assert res.status_code == 404


def test_record_payment_zero_amount_rejected():
    invoice = _create_invoice()
    res = client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": 0.0,
            "method": "bank_transfer",
            "payment_date": "2026-04-20",
        },
    )
    assert res.status_code == 422


def test_record_payment_negative_amount_rejected():
    invoice = _create_invoice()
    res = client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": -50.0,
            "method": "bank_transfer",
            "payment_date": "2026-04-20",
        },
    )
    assert res.status_code == 422


# -------------------------------------------------------
# Auto-status transitions
# -------------------------------------------------------

def test_full_payment_marks_invoice_paid():
    invoice = _create_invoice()
    res = client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": invoice["grand_total"],
            "method": "bank_transfer",
            "payment_date": "2026-04-20",
        },
    )
    assert res.status_code == 201

    fetched = client.get(f"/invoice/fetch/{invoice['invoice_id']}").json()
    assert fetched["status"] == "paid"


def test_partial_payment_does_not_mark_paid():
    invoice = _create_invoice()
    client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": 50.0,
            "method": "bank_transfer",
            "payment_date": "2026-04-20",
        },
    )
    fetched = client.get(f"/invoice/fetch/{invoice['invoice_id']}").json()
    assert fetched["status"] != "paid"


def test_deleting_payment_reverts_status_when_total_drops():
    invoice = _create_invoice()
    payment_res = client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": invoice["grand_total"],
            "method": "bank_transfer",
            "payment_date": "2026-04-20",
        },
    )
    assert client.get(f"/invoice/fetch/{invoice['invoice_id']}").json()["status"] == "paid"

    payment_id = payment_res.json()["payment_id"]
    del_res = client.delete(f"/payments/{payment_id}")
    assert del_res.status_code == 200

    fetched = client.get(f"/invoice/fetch/{invoice['invoice_id']}").json()
    assert fetched["status"] == "sent"


# -------------------------------------------------------
# List + summary
# -------------------------------------------------------

def test_list_payments_returns_list():
    res = client.get("/payments")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_invoice_payment_summary_zero_payments():
    invoice = _create_invoice()
    res = client.get(f"/payments/invoice/{invoice['invoice_id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["invoice_id"] == invoice["invoice_id"]
    assert body["grand_total"] == invoice["grand_total"]
    assert body["total_paid"] == 0.0
    assert body["outstanding_balance"] == invoice["grand_total"]
    assert body["payments"] == []


def test_invoice_payment_summary_partial_payment():
    invoice = _create_invoice()
    client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": 300.0,
            "method": "credit_card",
            "payment_date": "2026-04-20",
        },
    )
    res = client.get(f"/payments/invoice/{invoice['invoice_id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["total_paid"] == 300.0
    assert body["outstanding_balance"] == round(invoice["grand_total"] - 300.0, 2)
    assert len(body["payments"]) == 1


def test_invoice_payment_summary_unknown_invoice():
    res = client.get("/payments/invoice/no-such-invoice")
    assert res.status_code == 404


# -------------------------------------------------------
# Get / update / delete a single payment
# -------------------------------------------------------

def test_get_payment_by_id():
    invoice = _create_invoice()
    created = client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": 25.0,
            "method": "cash",
            "payment_date": "2026-04-20",
        },
    ).json()
    res = client.get(f"/payments/{created['payment_id']}")
    assert res.status_code == 200
    assert res.json()["payment_id"] == created["payment_id"]


def test_get_payment_not_found():
    res = client.get("/payments/does-not-exist")
    assert res.status_code == 404


def test_update_payment_amount():
    invoice = _create_invoice()
    created = client.post(
        "/payments",
        json={
            "invoice_id": invoice["invoice_id"],
            "amount": 25.0,
            "method": "cash",
            "payment_date": "2026-04-20",
        },
    ).json()
    res = client.put(
        f"/payments/{created['payment_id']}",
        json={"amount": 75.0, "reference": "txn-123"},
    )
    assert res.status_code == 200
    assert res.json()["amount"] == 75.0
    assert res.json()["reference"] == "txn-123"


def test_update_payment_not_found():
    res = client.put("/payments/does-not-exist", json={"amount": 1.0})
    assert res.status_code == 404


def test_delete_payment_not_found():
    res = client.delete("/payments/does-not-exist")
    assert res.status_code == 404

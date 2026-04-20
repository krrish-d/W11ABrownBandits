"""
Regression tests: each authenticated user must only see their own data.

Covers the owner-scoping rule applied across invoice, payment, dashboard,
audit and communication endpoints. Uses an isolated sqlite file so it
does not clash with other system tests.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app


TEST_DB_PATH = "./test_user_isolation.db"
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


def _signup(email: str) -> str:
    """Create a user and return their bearer token."""
    res = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "full_name": email},
    )
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _invoice_payload(buyer_email: str):
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
                "quantity": 1,
                "unit_price": 100.0,
                "tax_rate": 10.0,
            }
        ],
    }


@pytest.fixture
def two_users_with_invoices():
    alice_email = f"alice-{uuid.uuid4().hex[:6]}@example.com"
    bob_email = f"bob-{uuid.uuid4().hex[:6]}@example.com"
    alice_token = _signup(alice_email)
    bob_token = _signup(bob_email)

    alice_inv = client.post(
        "/invoice/create",
        json=_invoice_payload("alice-buyer@example.com"),
        headers=_auth(alice_token),
    ).json()
    bob_inv = client.post(
        "/invoice/create",
        json=_invoice_payload("bob-buyer@example.com"),
        headers=_auth(bob_token),
    ).json()

    return {
        "alice": {"token": alice_token, "invoice": alice_inv},
        "bob": {"token": bob_token, "invoice": bob_inv},
    }


# -------------------------------------------------------
# Invoices
# -------------------------------------------------------

def test_invoice_list_is_scoped_to_owner(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    alice_list = client.get("/invoice/list", headers=_auth(alice["token"])).json()
    bob_list = client.get("/invoice/list", headers=_auth(bob["token"])).json()

    alice_ids = {inv["invoice_id"] for inv in alice_list}
    bob_ids = {inv["invoice_id"] for inv in bob_list}

    assert alice["invoice"]["invoice_id"] in alice_ids
    assert bob["invoice"]["invoice_id"] not in alice_ids
    assert bob["invoice"]["invoice_id"] in bob_ids
    assert alice["invoice"]["invoice_id"] not in bob_ids


def test_invoice_fetch_cross_user_is_404(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    res = client.get(
        f"/invoice/fetch/{bob['invoice']['invoice_id']}",
        headers=_auth(alice["token"]),
    )
    assert res.status_code == 404


def test_invoice_update_cross_user_is_404(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    res = client.put(
        f"/invoice/update/{bob['invoice']['invoice_id']}",
        json={"buyer_name": "Hacked"},
        headers=_auth(alice["token"]),
    )
    assert res.status_code == 404


def test_invoice_delete_cross_user_is_404(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    res = client.delete(
        f"/invoice/delete/{bob['invoice']['invoice_id']}",
        headers=_auth(alice["token"]),
    )
    assert res.status_code == 404

    # Bob's invoice is still there for Bob
    res = client.get(
        f"/invoice/fetch/{bob['invoice']['invoice_id']}",
        headers=_auth(bob["token"]),
    )
    assert res.status_code == 200


def test_invoice_status_change_cross_user_is_404(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    res = client.put(
        f"/invoice/{bob['invoice']['invoice_id']}/status",
        params={"status": "paid"},
        headers=_auth(alice["token"]),
    )
    assert res.status_code == 404


# -------------------------------------------------------
# Payments
# -------------------------------------------------------

def test_payment_recording_blocked_on_other_users_invoice(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    res = client.post(
        "/payments",
        json={
            "invoice_id": bob["invoice"]["invoice_id"],
            "amount": 10.0,
            "method": "bank_transfer",
            "payment_date": "2026-04-20",
        },
        headers=_auth(alice["token"]),
    )
    assert res.status_code == 404


def test_payment_list_is_scoped_to_owner(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    # Each user records a payment on their own invoice
    for user in (alice, bob):
        res = client.post(
            "/payments",
            json={
                "invoice_id": user["invoice"]["invoice_id"],
                "amount": 10.0,
                "method": "bank_transfer",
                "payment_date": "2026-04-20",
            },
            headers=_auth(user["token"]),
        )
        assert res.status_code == 201, res.text

    alice_payments = client.get("/payments", headers=_auth(alice["token"])).json()
    alice_invoice_ids = {p["invoice_id"] for p in alice_payments}
    assert alice["invoice"]["invoice_id"] in alice_invoice_ids
    assert bob["invoice"]["invoice_id"] not in alice_invoice_ids


def test_payment_summary_cross_user_is_404(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    res = client.get(
        f"/payments/invoice/{bob['invoice']['invoice_id']}",
        headers=_auth(alice["token"]),
    )
    assert res.status_code == 404


# -------------------------------------------------------
# Dashboard
# -------------------------------------------------------

def test_dashboard_kpis_are_scoped_to_owner(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    alice_kpis = client.get("/dashboard/kpis", headers=_auth(alice["token"])).json()
    bob_kpis = client.get("/dashboard/kpis", headers=_auth(bob["token"])).json()

    # Each user should only count their own single invoice in the total
    assert alice_kpis["total_invoices"] == 1
    assert bob_kpis["total_invoices"] == 1
    assert alice_kpis["total_invoiced_all_time"] == pytest.approx(
        alice["invoice"]["grand_total"]
    )
    assert bob_kpis["total_invoiced_all_time"] == pytest.approx(
        bob["invoice"]["grand_total"]
    )


def test_dashboard_top_clients_are_scoped(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    alice_top = client.get("/dashboard/top-clients", headers=_auth(alice["token"])).json()
    bob_top = client.get("/dashboard/top-clients", headers=_auth(bob["token"])).json()

    # Each user has exactly one invoice with buyer "Buyer Co"; the grouping
    # should only reflect their own invoice.
    assert len(alice_top["top_clients"]) == 1
    assert len(bob_top["top_clients"]) == 1
    assert alice_top["top_clients"][0]["invoice_count"] == 1
    assert bob_top["top_clients"][0]["invoice_count"] == 1


# -------------------------------------------------------
# Audit
# -------------------------------------------------------

def test_audit_logs_are_scoped_to_caller(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    alice_logs = client.get("/audit", headers=_auth(alice["token"])).json()
    bob_logs = client.get("/audit", headers=_auth(bob["token"])).json()

    alice_entity_ids = {row["entity_id"] for row in alice_logs}
    bob_entity_ids = {row["entity_id"] for row in bob_logs}

    assert alice["invoice"]["invoice_id"] in alice_entity_ids
    assert bob["invoice"]["invoice_id"] not in alice_entity_ids
    assert bob["invoice"]["invoice_id"] in bob_entity_ids
    assert alice["invoice"]["invoice_id"] not in bob_entity_ids


# -------------------------------------------------------
# Clients
# -------------------------------------------------------

def test_clients_list_does_not_leak_across_users(two_users_with_invoices):
    alice = two_users_with_invoices["alice"]
    bob = two_users_with_invoices["bob"]

    alice_clients = client.get("/clients", headers=_auth(alice["token"])).json()
    bob_clients = client.get("/clients", headers=_auth(bob["token"])).json()

    alice_emails = {c["email"] for c in alice_clients}
    bob_emails = {c["email"] for c in bob_clients}

    # create_invoice auto-inserts the buyer as a reusable client
    assert "alice-buyer@example.com" in alice_emails
    assert "bob-buyer@example.com" not in alice_emails
    assert "bob-buyer@example.com" in bob_emails
    assert "alice-buyer@example.com" not in bob_emails

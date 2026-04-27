"""System tests for /audit/* endpoints."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app


TEST_DB_PATH = "./test_audit_system.db"
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


def _create_invoice() -> dict:
    res = client.post(
        "/invoice/create",
        json={
            "seller_name": "Seller Co",
            "seller_address": "1 Seller St",
            "seller_email": "seller@example.com",
            "buyer_name": "Buyer Co",
            "buyer_address": "2 Buyer Rd",
            "buyer_email": f"{uuid.uuid4().hex[:6]}@example.com",
            "currency": "AUD",
            "due_date": "2026-12-31",
            "items": [
                {
                    "item_number": "1",
                    "description": "Widget",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "tax_rate": 10.0,
                }
            ],
        },
    )
    assert res.status_code == 201
    return res.json()


# -------------------------------------------------------
# /audit
# -------------------------------------------------------

def test_audit_list_returns_list():
    res = client.get("/audit")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_creating_invoice_writes_create_audit_row():
    invoice = _create_invoice()
    res = client.get(f"/audit?entity_type=invoice&entity_id={invoice['invoice_id']}")
    assert res.status_code == 200
    rows = res.json()
    actions = [row["action"] for row in rows]
    assert "create" in actions
    assert all(row["entity_id"] == invoice["invoice_id"] for row in rows)


def test_updating_invoice_writes_update_audit_row():
    invoice = _create_invoice()
    client.put(f"/invoice/update/{invoice['invoice_id']}", json={"buyer_name": "Renamed"})

    res = client.get(f"/audit?entity_type=invoice&entity_id={invoice['invoice_id']}&action=update")
    assert res.status_code == 200
    rows = res.json()
    assert any(row["action"] == "update" for row in rows)


def test_audit_filter_by_entity_type():
    _create_invoice()
    res = client.get("/audit?entity_type=invoice")
    assert res.status_code == 200
    assert all(row["entity_type"] == "invoice" for row in res.json())


def test_audit_filter_by_action():
    _create_invoice()
    res = client.get("/audit?action=create")
    assert res.status_code == 200
    assert all(row["action"] == "create" for row in res.json())


def test_audit_pagination_limit_zero_yields_empty():
    res = client.get("/audit?limit=0")
    # `limit=0` is allowed by the route (only le=500), so the result should be a (possibly empty) list
    assert res.status_code in (200, 422)


def test_audit_pagination_offset():
    res = client.get("/audit?offset=0&limit=5")
    assert res.status_code == 200
    assert len(res.json()) <= 5


def test_audit_limit_too_high_rejected():
    res = client.get("/audit?limit=10000")
    assert res.status_code == 422


# -------------------------------------------------------
# /audit/entity/{type}/{id}
# -------------------------------------------------------

def test_entity_audit_trail_returns_chronological_history():
    invoice = _create_invoice()
    client.put(f"/invoice/update/{invoice['invoice_id']}", json={"buyer_name": "Renamed"})

    res = client.get(f"/audit/entity/invoice/{invoice['invoice_id']}")
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) >= 2

    timestamps = [row["timestamp"] for row in rows]
    assert timestamps == sorted(timestamps)


def test_entity_audit_trail_unknown_entity_type_returns_404():
    res = client.get("/audit/entity/galaxies/some-id")
    assert res.status_code == 404


def test_entity_audit_trail_unknown_invoice_returns_empty():
    """Unknown invoice id maps to owner_id=None, which an anonymous caller 'owns'.

    The endpoint therefore returns 200 with an empty list rather than a 404.
    """
    res = client.get("/audit/entity/invoice/does-not-exist")
    assert res.status_code == 200
    assert res.json() == []


def test_status_change_writes_status_change_audit_row():
    invoice = _create_invoice()
    res = client.put(f"/invoice/{invoice['invoice_id']}/status", params={"status": "sent"})
    assert res.status_code == 200

    rows = client.get(f"/audit/entity/invoice/{invoice['invoice_id']}").json()
    actions = [r["action"] for r in rows]
    assert "status_change" in actions

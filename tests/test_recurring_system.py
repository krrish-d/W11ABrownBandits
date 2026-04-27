"""System tests for /recurring/* endpoints and the manual trigger flow."""

import os
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app


TEST_DB_PATH = "./test_recurring_system.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="module", autouse=True)
def isolated_db():
    """Per-module isolated SQLite. Also redirects the scheduler's session
    factory into the same DB so that /recurring/trigger writes land here.
    """
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

    # Redirect scheduler's _get_db so the trigger endpoint writes to our test DB.
    from app.services import scheduler as scheduler_module
    original_get_db = scheduler_module._get_db
    scheduler_module._get_db = lambda: TestingSessionLocal()

    yield TestingSessionLocal

    scheduler_module._get_db = original_get_db
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


client = TestClient(app)


def _invoice_template() -> dict:
    """Return a valid InvoiceCreate-shaped payload."""
    return {
        "seller_name": "Recurring Seller",
        "seller_address": "1 Seller St",
        "seller_email": "seller@example.com",
        "buyer_name": "Recurring Buyer",
        "buyer_address": "2 Buyer Rd",
        "buyer_email": "buyer@example.com",
        "currency": "AUD",
        "due_date": "2026-06-01",
        "items": [
            {
                "item_number": "1",
                "description": "Monthly retainer",
                "quantity": 1,
                "unit_price": 1000.0,
                "tax_rate": 10.0,
            }
        ],
    }


def _create_rule(frequency: str = "monthly", next_run: date = None, end_date: date = None) -> dict:
    payload = {
        "name": f"Rule-{uuid.uuid4().hex[:6]}",
        "frequency": frequency,
        "next_run_date": (next_run or (date.today() + timedelta(days=10))).isoformat(),
        "invoice_template": _invoice_template(),
    }
    if end_date is not None:
        payload["end_date"] = end_date.isoformat()
    res = client.post("/recurring", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


# -------------------------------------------------------
# Create
# -------------------------------------------------------

@pytest.mark.parametrize("freq", ["daily", "weekly", "biweekly", "monthly", "quarterly", "annually"])
def test_create_recurring_rule_each_frequency(freq):
    rule = _create_rule(frequency=freq)
    assert rule["frequency"] == freq
    assert rule["is_active"] is True
    assert rule["recurring_id"]


def test_create_recurring_rejects_invalid_frequency():
    payload = {
        "name": "Bad",
        "frequency": "fortnightly",
        "next_run_date": date.today().isoformat(),
        "invoice_template": _invoice_template(),
    }
    res = client.post("/recurring", json=payload)
    assert res.status_code == 422


def test_create_recurring_rejects_invalid_invoice_template():
    """Template missing required InvoiceCreate fields should be rejected at create time."""
    payload = {
        "name": "Bad Template",
        "frequency": "monthly",
        "next_run_date": date.today().isoformat(),
        "invoice_template": {"seller_name": "Only field"},
    }
    res = client.post("/recurring", json=payload)
    assert res.status_code == 422
    assert "Invalid invoice_template" in res.json()["detail"]


# -------------------------------------------------------
# List / fetch / update / delete
# -------------------------------------------------------

def test_list_recurring_returns_list():
    res = client.get("/recurring")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_recurring_by_id():
    rule = _create_rule()
    res = client.get(f"/recurring/{rule['recurring_id']}")
    assert res.status_code == 200
    assert res.json()["recurring_id"] == rule["recurring_id"]


def test_get_recurring_not_found():
    res = client.get("/recurring/does-not-exist")
    assert res.status_code == 404


def test_update_recurring_name():
    rule = _create_rule()
    res = client.put(
        f"/recurring/{rule['recurring_id']}",
        json={"name": "Updated Rule Name"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Rule Name"


def test_update_recurring_invalid_frequency():
    rule = _create_rule()
    res = client.put(
        f"/recurring/{rule['recurring_id']}",
        json={"frequency": "fortnightly"},
    )
    assert res.status_code == 422


def test_update_recurring_invalid_template():
    rule = _create_rule()
    res = client.put(
        f"/recurring/{rule['recurring_id']}",
        json={"invoice_template": {"seller_name": "Only"}},
    )
    assert res.status_code == 422


def test_update_recurring_not_found():
    res = client.put("/recurring/does-not-exist", json={"name": "Ghost"})
    assert res.status_code == 404


def test_delete_recurring_success():
    rule = _create_rule()
    res = client.delete(f"/recurring/{rule['recurring_id']}")
    assert res.status_code == 200


def test_delete_recurring_not_found():
    res = client.delete("/recurring/does-not-exist")
    assert res.status_code == 404


# -------------------------------------------------------
# Manual trigger
# -------------------------------------------------------

def test_trigger_endpoint_returns_202():
    res = client.post("/recurring/trigger")
    assert res.status_code == 202
    assert "triggered" in res.json()["message"].lower()


def test_trigger_generates_invoice_for_due_rule():
    """Rule whose next_run_date is in the past should produce a new invoice."""
    rule = _create_rule(next_run=date.today() - timedelta(days=1))

    invoices_before = client.get("/invoice/list").json()
    before_ids = {inv["invoice_id"] for inv in invoices_before}

    trigger = client.post("/recurring/trigger")
    assert trigger.status_code == 202

    invoices_after = client.get("/invoice/list").json()
    after_ids = {inv["invoice_id"] for inv in invoices_after}
    # At least one new invoice was produced by the rule firing
    assert len(after_ids - before_ids) >= 1

    refreshed = client.get(f"/recurring/{rule['recurring_id']}").json()
    # next_run_date moved forward off the original (today - 1d) value
    assert refreshed["next_run_date"] != (date.today() - timedelta(days=1)).isoformat()
    assert refreshed["last_run_date"] == date.today().isoformat()


def test_trigger_deactivates_rule_past_end_date():
    rule = _create_rule(
        next_run=date.today() - timedelta(days=1),
        end_date=date.today() - timedelta(days=2),
    )
    client.post("/recurring/trigger")

    refreshed = client.get(f"/recurring/{rule['recurring_id']}").json()
    assert refreshed["is_active"] is False

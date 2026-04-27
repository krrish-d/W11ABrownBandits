"""System tests for the invoice routes not covered by test_invoice_system.py:

- PUT /invoice/{id}/status
- POST /invoice/check-overdue
- GET /invoice/list filters / sorting / pagination
- POST /invoice/parse-file (json / csv / xml / unknown sniffing)
- GET /invoice/import/{token} (single-use, expired, missing)
"""

import io
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models.invoice_import import InvoiceImportToken
from main import app


TEST_DB_PATH = "./test_invoice_extra.db"
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
    yield TestingSessionLocal
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


client = TestClient(app)


def _invoice_payload(**overrides) -> dict:
    base = {
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
    }
    base.update(overrides)
    return base


def _create_invoice(**overrides) -> dict:
    res = client.post("/invoice/create", json=_invoice_payload(**overrides))
    assert res.status_code == 201
    return res.json()


# =======================================================
# PUT /invoice/{id}/status
# =======================================================

def test_status_update_to_sent():
    inv = _create_invoice()
    res = client.put(f"/invoice/{inv['invoice_id']}/status", params={"status": "sent"})
    assert res.status_code == 200
    assert res.json()["status"] == "sent"


def test_status_update_invalid_value_returns_422():
    inv = _create_invoice()
    res = client.put(f"/invoice/{inv['invoice_id']}/status", params={"status": "shipped"})
    assert res.status_code == 422


def test_status_update_unknown_invoice_returns_404():
    res = client.put("/invoice/does-not-exist/status", params={"status": "sent"})
    assert res.status_code == 404


# =======================================================
# POST /invoice/check-overdue
# =======================================================

def test_check_overdue_flips_past_due_invoices():
    """A past-due invoice in 'sent' status should flip to 'overdue'."""
    inv = _create_invoice(due_date="2020-01-01")
    # Move it to 'sent' first (not draft) so it's a clearer overdue candidate
    client.put(f"/invoice/{inv['invoice_id']}/status", params={"status": "sent"})

    res = client.post("/invoice/check-overdue")
    assert res.status_code == 200
    assert "marked_overdue" in res.json()

    fetched = client.get(f"/invoice/fetch/{inv['invoice_id']}").json()
    assert fetched["status"] == "overdue"


def test_check_overdue_does_not_touch_paid_invoices():
    inv = _create_invoice(due_date="2020-01-01")
    client.put(f"/invoice/{inv['invoice_id']}/status", params={"status": "paid"})

    client.post("/invoice/check-overdue")
    fetched = client.get(f"/invoice/fetch/{inv['invoice_id']}").json()
    assert fetched["status"] == "paid"


# =======================================================
# GET /invoice/list filters / sorting / pagination
# =======================================================

def test_list_filter_by_status():
    inv = _create_invoice()
    client.put(f"/invoice/{inv['invoice_id']}/status", params={"status": "cancelled"})

    res = client.get("/invoice/list?status=cancelled")
    assert res.status_code == 200
    statuses = {row["status"] for row in res.json()}
    assert statuses == {"cancelled"} or statuses.issubset({"cancelled"})


def test_list_filter_by_search_invoice_number():
    inv = _create_invoice()
    res = client.get(f"/invoice/list?search={inv['invoice_number']}")
    assert res.status_code == 200
    numbers = [row["invoice_number"] for row in res.json()]
    assert inv["invoice_number"] in numbers


def test_list_filter_by_min_amount_excludes_smaller():
    cheap = _create_invoice(items=[{
        "item_number": "1", "description": "Cheap", "quantity": 1,
        "unit_price": 10.0, "tax_rate": 0.0,
    }])
    expensive = _create_invoice(items=[{
        "item_number": "1", "description": "Expensive", "quantity": 1,
        "unit_price": 5000.0, "tax_rate": 0.0,
    }])

    res = client.get("/invoice/list?min_amount=1000")
    assert res.status_code == 200
    ids = {row["invoice_id"] for row in res.json()}
    assert expensive["invoice_id"] in ids
    assert cheap["invoice_id"] not in ids


def test_list_pagination_page_size():
    for _ in range(3):
        _create_invoice()
    res = client.get("/invoice/list?page=1&page_size=2")
    assert res.status_code == 200
    assert len(res.json()) <= 2


def test_list_sort_by_grand_total_desc():
    _create_invoice(items=[{
        "item_number": "1", "description": "A", "quantity": 1,
        "unit_price": 9999.0, "tax_rate": 0.0,
    }])
    res = client.get("/invoice/list?sort_by=grand_total&sort_order=desc&page_size=200")
    assert res.status_code == 200
    totals = [row["grand_total"] for row in res.json()]
    assert totals == sorted(totals, reverse=True)


def test_list_invalid_page_size_rejected():
    res = client.get("/invoice/list?page_size=0")
    assert res.status_code == 422


# =======================================================
# POST /invoice/parse-file
# =======================================================

def test_parse_file_json():
    payload = {
        "seller_name": "Seller Co",
        "seller_address": "addr",
        "seller_email": "seller@example.com",
        "buyer_name": "Buyer Co",
        "buyer_address": "addr",
        "buyer_email": "buyer@example.com",
        "currency": "AUD",
        "due_date": "2026-12-31",
        "items": [{"item_number": "1", "description": "X", "quantity": 1,
                   "unit_price": 100, "tax_rate": 10}],
    }
    res = client.post(
        "/invoice/parse-file",
        files={"file": ("invoice.json", json.dumps(payload), "application/json")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["seller_name"] == "Seller Co"
    assert body["buyer_name"] == "Buyer Co"


def test_parse_file_csv():
    csv_text = (
        "invoice_number,currency,seller_name,seller_address,seller_email,"
        "buyer_name,buyer_address,buyer_email,issue_date,due_date,subtotal,tax_total,grand_total\n"
        "INV-CSV-1,AUD,Seller Co,1 Seller St,seller@example.com,"
        "Buyer Co,2 Buyer Rd,buyer@example.com,2026-01-01,2026-12-31,100,10,110\n"
        "\n"
        "item_number,description,quantity,unit_price,tax_rate,line_total\n"
        "1,Widget,1,100,10,100\n"
    )
    res = client.post(
        "/invoice/parse-file",
        files={"file": ("invoice.csv", csv_text, "text/csv")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["seller_name"] == "Seller Co"
    assert body["buyer_email"] == "buyer@example.com"


def test_parse_file_generic_xml():
    xml = """<?xml version='1.0' encoding='UTF-8'?>
<Invoice>
  <SellerName>Seller Co</SellerName>
  <SellerAddress>addr</SellerAddress>
  <SellerEmail>seller@example.com</SellerEmail>
  <BuyerName>Buyer Co</BuyerName>
  <BuyerAddress>addr</BuyerAddress>
  <BuyerEmail>buyer@example.com</BuyerEmail>
  <Currency>AUD</Currency>
  <DueDate>2026-12-31</DueDate>
</Invoice>"""
    res = client.post(
        "/invoice/parse-file",
        files={"file": ("invoice.xml", xml, "application/xml")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("seller_name") == "Seller Co"
    assert body.get("buyer_name") == "Buyer Co"


def test_parse_file_unknown_extension_rejected():
    res = client.post(
        "/invoice/parse-file",
        files={"file": ("rubbish.txt", "this is not a real invoice", "text/plain")},
    )
    assert res.status_code == 400


# =======================================================
# GET /invoice/import/{token}
# =======================================================

def _seed_token(session_factory, invoice_id: str, *, expires_in_days: int = 7) -> str:
    """Insert a valid InvoiceImportToken directly and return its token string."""
    db = session_factory()
    try:
        token_value = secrets.token_urlsafe(16)
        db.add(InvoiceImportToken(
            invoice_id=invoice_id,
            token=token_value,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        ))
        db.commit()
        return token_value
    finally:
        db.close()


def _seed_expired_token(session_factory, invoice_id: str) -> str:
    db = session_factory()
    try:
        token_value = secrets.token_urlsafe(16)
        db.add(InvoiceImportToken(
            invoice_id=invoice_id,
            token=token_value,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        ))
        db.commit()
        return token_value
    finally:
        db.close()


def test_import_token_unknown_returns_404(isolated_db):
    res = client.get("/invoice/import/no-such-token")
    assert res.status_code == 404


def test_import_token_happy_path_creates_copy(isolated_db):
    inv = _create_invoice()
    # Mark the original as 'sent' so the import flips it to 'viewed'
    client.put(f"/invoice/{inv['invoice_id']}/status", params={"status": "sent"})

    token = _seed_token(isolated_db, inv["invoice_id"])
    res = client.get(f"/invoice/import/{token}")
    assert res.status_code == 200
    body = res.json()
    assert body["invoice_id"] != inv["invoice_id"]
    assert body["invoice_number"].startswith("IMP-")
    assert body["buyer_name"] == inv["buyer_name"]

    refreshed = client.get(f"/invoice/fetch/{inv['invoice_id']}").json()
    assert refreshed["status"] == "viewed"


def test_import_token_can_only_be_used_once(isolated_db):
    inv = _create_invoice()
    token = _seed_token(isolated_db, inv["invoice_id"])

    first = client.get(f"/invoice/import/{token}")
    assert first.status_code == 200

    second = client.get(f"/invoice/import/{token}")
    assert second.status_code == 410
    assert "already been used" in second.json()["detail"].lower()


def test_import_token_expired_returns_410(isolated_db):
    inv = _create_invoice()
    token = _seed_expired_token(isolated_db, inv["invoice_id"])

    res = client.get(f"/invoice/import/{token}")
    assert res.status_code == 410
    assert "expired" in res.json()["detail"].lower()

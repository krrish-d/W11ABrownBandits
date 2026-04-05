import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from main import app

# In-memory test database
TEST_DATABASE_URL = "sqlite:///./test_invoices.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

SAMPLE_INVOICE = {
    "client_name": "Test Client",
    "client_email": "test@example.com",
    "currency": "AUD",
    "due_date": "2026-06-01",
    "notes": "Test note",
    "items": [
        {
            "description": "Laptop",
            "quantity": 2,
            "unit_price": 500.0,
            "tax_rate": 10.0
        }
    ]
}

def create_invoice():
    res = client.post("/invoice/create", json=SAMPLE_INVOICE)
    assert res.status_code == 201
    return res.json()["invoice_id"]


# POST

def test_create_invoice_success():
    res = client.post("/invoice/create", json=SAMPLE_INVOICE)
    assert res.status_code == 201
    data = res.json()
    assert data["client_name"] == "Test Client"
    assert data["subtotal"] == 1000.0
    assert data["tax_total"] == 100.0
    assert data["grand_total"] == 1100.0

def test_create_invoice_has_id():
    res = client.post("/invoice/create", json=SAMPLE_INVOICE)
    assert res.status_code == 201
    assert "invoice_id" in res.json()
    assert "invoice_number" in res.json()

def test_create_invoice_multiple_items():
    payload = {
        **SAMPLE_INVOICE,
        "items": [
            {"description": "Item A", "quantity": 1, "unit_price": 100.0, "tax_rate": 10.0},
            {"description": "Item B", "quantity": 3, "unit_price": 50.0, "tax_rate": 5.0}
        ]
    }
    res = client.post("/invoice/create", json=payload)
    assert res.status_code == 201
    assert len(res.json()["items"]) == 2

def test_create_invoice_unique_ids():
    id1 = client.post("/invoice/create", json=SAMPLE_INVOICE).json()["invoice_id"]
    id2 = client.post("/invoice/create", json=SAMPLE_INVOICE).json()["invoice_id"]
    assert id1 != id2

def test_create_invoice_missing_client_name():
    payload = {**SAMPLE_INVOICE}
    del payload["client_name"]
    res = client.post("/invoice/create", json=payload)
    assert res.status_code == 422

def test_create_invoice_missing_items_field():
    payload = {**SAMPLE_INVOICE}
    del payload["items"]
    res = client.post("/invoice/create", json=payload)
    assert res.status_code == 422


# GET list

def test_list_invoices():
    res = client.get("/invoice/list")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# GET single

def test_get_invoice_json():
    invoice_id = create_invoice()
    res = client.get(f"/invoice/fetch/{invoice_id}")
    assert res.status_code == 200
    assert res.json()["invoice_id"] == invoice_id

def test_get_invoice_format_json():
    invoice_id = create_invoice()
    res = client.get(f"/invoice/fetch/{invoice_id}?format=json")
    assert res.status_code == 200
    assert res.json()["client_name"] == "Test Client"

def test_get_invoice_format_ubl():
    invoice_id = create_invoice()
    res = client.get(f"/invoice/fetch/{invoice_id}?format=ubl")
    assert res.status_code == 200
    assert "application/xml" in res.headers["content-type"]
    assert b"UBLVersionID" in res.content

def test_get_invoice_format_xml():
    invoice_id = create_invoice()
    res = client.get(f"/invoice/fetch/{invoice_id}?format=xml")
    assert res.status_code == 200
    assert "application/xml" in res.headers["content-type"]
    assert b"ClientName" in res.content

def test_get_invoice_format_csv():
    invoice_id = create_invoice()
    res = client.get(f"/invoice/fetch/{invoice_id}?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert b"Test Client" in res.content

def test_get_invoice_format_pdf():
    invoice_id = create_invoice()
    res = client.get(f"/invoice/fetch/{invoice_id}?format=pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content[:4] == b"%PDF"

def test_get_invoice_not_found():
    res = client.get("/invoice/fetch/does-not-exist")
    assert res.status_code == 404

def test_get_invoice_not_found_ubl():
    res = client.get("/invoice/fetch/does-not-exist?format=ubl")
    assert res.status_code == 404

def test_get_invoice_not_found_csv():
    res = client.get("/invoice/fetch/does-not-exist?format=csv")
    assert res.status_code == 404

def test_get_invoice_not_found_pdf():
    res = client.get("/invoice/fetch/does-not-exist?format=pdf")
    assert res.status_code == 404


# PUT

def test_update_invoice_name():
    invoice_id = create_invoice()
    res = client.put(f"/invoice/update/{invoice_id}", json={"client_name": "Updated"})
    assert res.status_code == 200
    assert res.json()["client_name"] == "Updated"

def test_update_invoice_email():
    invoice_id = create_invoice()
    res = client.put(f"/invoice/update/{invoice_id}", json={"client_email": "new@email.com"})
    assert res.status_code == 200
    assert res.json()["client_email"] == "new@email.com"

def test_update_invoice_not_found():
    res = client.put("/invoice/update/does-not-exist", json={"client_name": "Ghost"})
    assert res.status_code == 404


# DELETE

def test_delete_invoice():
    invoice_id = create_invoice()
    res = client.delete(f"/invoice/delete/{invoice_id}")
    assert res.status_code == 200
    assert "deleted" in res.json()["message"]

def test_delete_invoice_gone():
    invoice_id = create_invoice()
    client.delete(f"/invoice/delete/{invoice_id}")
    res = client.get(f"/invoice/fetch/{invoice_id}")
    assert res.status_code == 404

def test_delete_invoice_not_found():
    res = client.delete("/invoice/delete/does-not-exist")
    assert res.status_code == 404


# Health

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
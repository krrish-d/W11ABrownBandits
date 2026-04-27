"""System tests for /clients/* endpoints."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app


TEST_DB_PATH = "./test_clients_system.db"
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


def _signup_and_token() -> str:
    email = f"owner-{uuid.uuid4().hex[:6]}@example.com"
    res = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "full_name": "Owner"},
    )
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _client_payload(**overrides) -> dict:
    base = {
        "name": "Acme Corp",
        "email": f"acme-{uuid.uuid4().hex[:6]}@example.com",
        "address": "1 Acme Way",
        "tax_id": "12345678901",
        "currency": "AUD",
        "payment_terms": 30,
        "notes": "Long-time customer",
    }
    base.update(overrides)
    return base


# -------------------------------------------------------
# Create
# -------------------------------------------------------

def test_create_client_anonymous():
    res = client.post("/clients", json=_client_payload(name="Anon Client"))
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Anon Client"
    assert body["client_id"]
    assert body["owner_id"] is None


def test_create_client_authenticated():
    token = _signup_and_token()
    res = client.post(
        "/clients",
        json=_client_payload(name="Owned Client"),
        headers=_auth(token),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Owned Client"
    assert body["owner_id"] is not None


def test_create_client_missing_required_fields():
    res = client.post("/clients", json={"name": "No Email"})
    assert res.status_code == 422


def test_create_client_default_currency_and_terms():
    res = client.post(
        "/clients",
        json={
            "name": "Bare Bones",
            "email": f"bare-{uuid.uuid4().hex[:6]}@example.com",
        },
    )
    assert res.status_code == 201
    assert res.json()["currency"] == "AUD"
    assert res.json()["payment_terms"] == 30


# -------------------------------------------------------
# List + search
# -------------------------------------------------------

def test_list_clients_returns_list():
    res = client.get("/clients")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_list_clients_search_by_name():
    unique = f"SearchableCo-{uuid.uuid4().hex[:6]}"
    client.post(
        "/clients",
        json=_client_payload(name=unique),
    )
    res = client.get(f"/clients?search={unique}")
    assert res.status_code == 200
    names = [c["name"] for c in res.json()]
    assert unique in names


def test_list_clients_search_by_email():
    email = f"searchable-{uuid.uuid4().hex[:6]}@example.com"
    client.post("/clients", json=_client_payload(email=email))
    res = client.get(f"/clients?search={email}")
    assert res.status_code == 200
    emails = [c["email"] for c in res.json()]
    assert email in emails


# -------------------------------------------------------
# Fetch by id
# -------------------------------------------------------

def test_get_client_by_id():
    created = client.post("/clients", json=_client_payload(name="Findable")).json()
    res = client.get(f"/clients/{created['client_id']}")
    assert res.status_code == 200
    assert res.json()["name"] == "Findable"


def test_get_client_not_found():
    res = client.get("/clients/does-not-exist")
    assert res.status_code == 404


# -------------------------------------------------------
# Update
# -------------------------------------------------------

def test_update_client_name():
    created = client.post("/clients", json=_client_payload(name="Old Name")).json()
    res = client.put(
        f"/clients/{created['client_id']}",
        json={"name": "New Name"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"


def test_update_client_payment_terms():
    created = client.post("/clients", json=_client_payload()).json()
    res = client.put(
        f"/clients/{created['client_id']}",
        json={"payment_terms": 60},
    )
    assert res.status_code == 200
    assert res.json()["payment_terms"] == 60


def test_update_client_not_found():
    res = client.put("/clients/does-not-exist", json={"name": "Ghost"})
    assert res.status_code == 404


# -------------------------------------------------------
# Delete
# -------------------------------------------------------

def test_delete_client_success():
    created = client.post("/clients", json=_client_payload(name="To Delete")).json()
    res = client.delete(f"/clients/{created['client_id']}")
    assert res.status_code == 200
    assert "deleted" in res.json()["message"].lower()


def test_delete_client_then_fetch_404():
    created = client.post("/clients", json=_client_payload(name="To Delete")).json()
    client.delete(f"/clients/{created['client_id']}")
    res = client.get(f"/clients/{created['client_id']}")
    assert res.status_code == 404


def test_delete_client_not_found():
    res = client.delete("/clients/does-not-exist")
    assert res.status_code == 404

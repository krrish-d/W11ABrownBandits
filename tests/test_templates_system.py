"""System tests for /templates/* endpoints (covers default-flag handling)."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app


TEST_DB_PATH = "./test_templates_system.db"
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


def _payload(**overrides) -> dict:
    base = {
        "name": f"Tmpl-{uuid.uuid4().hex[:6]}",
        "primary_colour": "#2563eb",
        "secondary_colour": "#1e40af",
        "footer_text": "Thank you for your business",
        "payment_terms_text": "Net 30",
        "bank_details": "BSB 000-000 Acct 123456789",
        "is_default": False,
    }
    base.update(overrides)
    return base


# -------------------------------------------------------
# Create
# -------------------------------------------------------

def test_create_template_success():
    res = client.post("/templates", json=_payload(name="Brand A"))
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Brand A"
    assert body["is_default"] is False
    assert body["template_id"]


def test_create_template_missing_name():
    res = client.post("/templates", json={"primary_colour": "#fff"})
    assert res.status_code == 422


def test_create_template_uses_default_colours():
    res = client.post("/templates", json={"name": "ColourFreeTmpl"})
    assert res.status_code == 201
    body = res.json()
    assert body["primary_colour"] == "#2563eb"
    assert body["secondary_colour"] == "#1e40af"


# -------------------------------------------------------
# List / fetch
# -------------------------------------------------------

def test_list_templates_returns_list():
    res = client.get("/templates")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_template_by_id():
    created = client.post("/templates", json=_payload()).json()
    res = client.get(f"/templates/{created['template_id']}")
    assert res.status_code == 200
    assert res.json()["template_id"] == created["template_id"]


def test_get_template_not_found():
    res = client.get("/templates/does-not-exist")
    assert res.status_code == 404


# -------------------------------------------------------
# Update
# -------------------------------------------------------

def test_update_template_name():
    created = client.post("/templates", json=_payload(name="Old")).json()
    res = client.put(
        f"/templates/{created['template_id']}",
        json={"name": "New"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "New"


def test_update_template_not_found():
    res = client.put("/templates/does-not-exist", json={"name": "X"})
    assert res.status_code == 404


# -------------------------------------------------------
# Delete
# -------------------------------------------------------

def test_delete_template_success():
    created = client.post("/templates", json=_payload()).json()
    res = client.delete(f"/templates/{created['template_id']}")
    assert res.status_code == 200


def test_delete_template_then_fetch_404():
    created = client.post("/templates", json=_payload()).json()
    client.delete(f"/templates/{created['template_id']}")
    res = client.get(f"/templates/{created['template_id']}")
    assert res.status_code == 404


def test_delete_template_not_found():
    res = client.delete("/templates/does-not-exist")
    assert res.status_code == 404


# -------------------------------------------------------
# is_default flag handling
# -------------------------------------------------------

def test_creating_second_default_unsets_first():
    """Only one template per owner should hold is_default=True at any time."""
    first = client.post("/templates", json=_payload(name="First", is_default=True)).json()
    assert first["is_default"] is True

    second = client.post("/templates", json=_payload(name="Second", is_default=True)).json()
    assert second["is_default"] is True

    refreshed_first = client.get(f"/templates/{first['template_id']}").json()
    assert refreshed_first["is_default"] is False


def test_updating_template_to_default_unsets_previous_default():
    first = client.post("/templates", json=_payload(name="First", is_default=True)).json()
    second = client.post("/templates", json=_payload(name="Second", is_default=False)).json()

    res = client.put(
        f"/templates/{second['template_id']}",
        json={"is_default": True},
    )
    assert res.status_code == 200
    assert res.json()["is_default"] is True

    refreshed_first = client.get(f"/templates/{first['template_id']}").json()
    assert refreshed_first["is_default"] is False

"""System tests for /auth/* endpoints (signup, login, me, admin user management)."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from main import app


TEST_DB_PATH = "./test_auth_system.db"
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


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _signup(email: str, password: str = "password123", full_name: str = "Test User", role: str = "viewer") -> dict:
    res = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "full_name": full_name, "role": role},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# -------------------------------------------------------
# Signup
# -------------------------------------------------------

def test_signup_returns_token_and_user():
    email = _unique_email()
    res = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "full_name": "New User"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["full_name"] == "New User"
    assert data["user"]["role"] == "viewer"
    assert data["user"]["is_active"] is True


def test_signup_duplicate_email_rejected():
    email = _unique_email()
    _signup(email)
    res = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "full_name": "Other"},
    )
    assert res.status_code == 400
    assert "already registered" in res.json()["detail"].lower()


def test_signup_short_password_rejected():
    res = client.post(
        "/auth/signup",
        json={"email": _unique_email(), "password": "short", "full_name": "X"},
    )
    assert res.status_code == 422


# -------------------------------------------------------
# Login
# -------------------------------------------------------

def test_login_success_returns_token():
    email = _unique_email()
    _signup(email, password="password123")

    res = client.post(
        "/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == email


def test_login_wrong_password_returns_401():
    email = _unique_email()
    _signup(email, password="password123")

    res = client.post(
        "/auth/login",
        data={"username": email, "password": "wrong-password"},
    )
    assert res.status_code == 401


def test_login_unknown_user_returns_401():
    res = client.post(
        "/auth/login",
        data={"username": "ghost@nowhere.example.com", "password": "password123"},
    )
    assert res.status_code == 401


# -------------------------------------------------------
# /auth/me
# -------------------------------------------------------

def test_me_requires_auth():
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_returns_current_user():
    email = _unique_email()
    token = _signup(email)["access_token"]
    res = client.get("/auth/me", headers=_auth(token))
    assert res.status_code == 200
    assert res.json()["email"] == email


def test_me_with_invalid_token():
    res = client.get("/auth/me", headers=_auth("not.a.valid.token"))
    assert res.status_code == 401


def test_update_me_updates_full_name():
    token = _signup(_unique_email())["access_token"]
    res = client.put(
        "/auth/me",
        json={"full_name": "Updated Name"},
        headers=_auth(token),
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Updated Name"


def test_update_me_role_change_silently_ignored_for_viewer():
    """Regular users cannot escalate themselves to admin."""
    token = _signup(_unique_email())["access_token"]
    res = client.put(
        "/auth/me",
        json={"role": "admin"},
        headers=_auth(token),
    )
    assert res.status_code == 200
    assert res.json()["role"] == "viewer"


# -------------------------------------------------------
# Admin endpoints
# -------------------------------------------------------

def test_list_users_forbidden_for_viewer():
    token = _signup(_unique_email())["access_token"]
    res = client.get("/auth/users", headers=_auth(token))
    assert res.status_code == 403


def test_list_users_succeeds_for_admin():
    admin_token = _signup(_unique_email("admin"), role="admin")["access_token"]
    res = client.get("/auth/users", headers=_auth(admin_token))
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1


def test_admin_can_update_other_user():
    admin_token = _signup(_unique_email("admin"), role="admin")["access_token"]

    target = _signup(_unique_email("target"))
    target_user_id = target["user"]["user_id"]

    res = client.put(
        f"/auth/users/{target_user_id}",
        json={"full_name": "Renamed By Admin", "is_active": False},
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Renamed By Admin"
    assert res.json()["is_active"] is False


def test_admin_update_unknown_user_returns_404():
    admin_token = _signup(_unique_email("admin"), role="admin")["access_token"]
    res = client.put(
        "/auth/users/does-not-exist",
        json={"full_name": "X"},
        headers=_auth(admin_token),
    )
    assert res.status_code == 404


def test_login_deactivated_user_returns_403():
    """Deactivated users should not be able to log in."""
    admin_token = _signup(_unique_email("admin"), role="admin")["access_token"]
    target_email = _unique_email("deactivated")
    target = _signup(target_email)

    client.put(
        f"/auth/users/{target['user']['user_id']}",
        json={"is_active": False},
        headers=_auth(admin_token),
    )

    res = client.post(
        "/auth/login",
        data={"username": target_email, "password": "password123"},
    )
    assert res.status_code == 403

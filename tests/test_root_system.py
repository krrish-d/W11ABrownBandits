"""System tests for the top-level utility endpoints."""

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root_returns_welcome_payload():
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert "message" in body
    assert "docs" in body
    assert "version" in body


def test_root_message_mentions_e_invoice():
    res = client.get("/")
    assert "E-Invoice" in res.json()["message"]


def test_health_endpoint_healthy():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

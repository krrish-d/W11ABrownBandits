from fastapi.testclient import TestClient
from main import app


client = TestClient(app)

VALID_UBL_XML = """<?xml version='1.0' encoding='UTF-8'?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>INV-SYS-001</cbc:ID>
</Invoice>"""


class DummySMTP:
    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        return None

    def login(self, *_args, **_kwargs):
        return None

    def send_message(self, *_args, **_kwargs):
        return None


def test_communicate_send_success(monkeypatch):
    monkeypatch.setenv("GMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password")
    monkeypatch.setattr("app.services.communicate.smtplib.SMTP", DummySMTP)

    response = client.post("/communicate/send", json={
        "invoice_xml": VALID_UBL_XML,
        "recipient_email": "receiver@example.com"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
    assert data["invoice_id"] == "INV-SYS-001"
    assert data["recipient_email"] == "receiver@example.com"
    assert "timestamp" in data


def test_communicate_logs_returns_list():
    response = client.get("/communicate/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_communicate_health_check():
    response = client.get("/communicate/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_communicate_send_invalid_xml(monkeypatch):
    monkeypatch.setenv("GMAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password")

    response = client.post("/communicate/send", json={
        "invoice_xml": "<not valid xml",
        "recipient_email": "receiver@example.com"
    })
    assert response.status_code == 400
    assert "Invalid XML" in response.json()["detail"]

"""System tests for the Xero / QuickBooks webhook stub receivers."""

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


# -------------------------------------------------------
# /webhooks/xero
# -------------------------------------------------------

def test_xero_webhook_accepts_payload():
    res = client.post(
        "/webhooks/xero",
        json={"events": [{"resourceType": "Invoice", "resourceId": "abc", "eventCategory": "INVOICE"}]},
    )
    assert res.status_code == 200
    assert res.json() == {"received": True}


def test_xero_webhook_accepts_empty_object():
    res = client.post("/webhooks/xero", json={})
    assert res.status_code == 200
    assert res.json()["received"] is True


# -------------------------------------------------------
# /webhooks/quickbooks
# -------------------------------------------------------

def test_quickbooks_webhook_accepts_payload():
    res = client.post(
        "/webhooks/quickbooks",
        json={"eventNotifications": [{"realmId": "123", "dataChangeEvent": {}}]},
    )
    assert res.status_code == 200
    assert res.json() == {"received": True}


def test_quickbooks_webhook_accepts_empty_object():
    res = client.post("/webhooks/quickbooks", json={})
    assert res.status_code == 200
    assert res.json()["received"] is True

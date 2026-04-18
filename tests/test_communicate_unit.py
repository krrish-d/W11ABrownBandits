import pytest
from app.services.communicate import extract_invoice_id, send_invoice_email


VALID_UBL_XML = """<?xml version='1.0' encoding='UTF-8'?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>INV-UNIT-001</cbc:ID>
</Invoice>"""


def test_extract_invoice_id_valid():
    assert extract_invoice_id(VALID_UBL_XML) == "INV-UNIT-001"


def test_extract_invoice_id_invalid_xml():
    with pytest.raises(ValueError, match="Invalid XML"):
        extract_invoice_id("<not valid xml")


def test_extract_invoice_id_missing_id():
    xml_without_id = """<?xml version='1.0' encoding='UTF-8'?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
</Invoice>"""
    with pytest.raises(ValueError, match="Invoice ID is missing"):
        extract_invoice_id(xml_without_id)


def test_send_invoice_email_missing_credentials(monkeypatch):
    monkeypatch.delenv("GMAIL_USERNAME", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="Missing Gmail SMTP credentials"):
        send_invoice_email(VALID_UBL_XML, "recipient@example.com")

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

VALID_UBL_XML = """<?xml version='1.0' encoding='UTF-8'?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:ID>INV-001</cbc:ID>
  <cbc:IssueDate>2026-03-16</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>AUD</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>ABC Pty Ltd</cbc:Name>
      </cac:PartyName>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>XYZ Pty Ltd</cbc:Name>
      </cac:PartyName>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="AUD">100.0</cbc:LineExtensionAmount>
    <cbc:TaxInclusiveAmount currencyID="AUD">110.0</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="AUD">110.0</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="EA">2</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="AUD">100.0</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Description>Consulting</cbc:Description>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount currencyID="AUD">50.0</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>
</Invoice>"""

MISSING_FIELDS_XML = """<?xml version='1.0' encoding='UTF-8'?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
</Invoice>"""

WRONG_TOTALS_XML = """<?xml version='1.0' encoding='UTF-8'?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:ID>INV-001</cbc:ID>
  <cbc:IssueDate>2026-03-16</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>AUD</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>ABC Pty Ltd</cbc:Name>
      </cac:PartyName>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>XYZ Pty Ltd</cbc:Name>
      </cac:PartyName>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="AUD">999.0</cbc:LineExtensionAmount>
    <cbc:TaxInclusiveAmount currencyID="AUD">110.0</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="AUD">110.0</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="EA">2</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="AUD">100.0</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Description>Consulting</cbc:Description>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount currencyID="AUD">50.0</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>
</Invoice>"""


# -------------------------------------------------------
# POST /validate — UBL ruleset (default)
# -------------------------------------------------------
def test_validate_valid_invoice_ubl():
    response = client.post("/validate", json={
        "invoice_xml": VALID_UBL_XML
    })
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["ruleset"] == "ubl"
    assert isinstance(data["errors"], list)


def test_validate_invalid_xml():
    response = client.post("/validate", json={
        "invoice_xml": "<not valid xml"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


def test_validate_missing_fields():
    response = client.post("/validate", json={
        "invoice_xml": MISSING_FIELDS_XML
    })
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


def test_validate_wrong_totals():
    response = client.post("/validate", json={
        "invoice_xml": WRONG_TOTALS_XML
    })
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


# -------------------------------------------------------
# POST /validate — PEPPOL ruleset
# -------------------------------------------------------
def test_validate_peppol_ruleset():
    response = client.post("/validate", json={
        "invoice_xml": VALID_UBL_XML,
        "ruleset": "peppol"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ruleset"] == "peppol"
    assert isinstance(data["errors"], list)


def test_validate_peppol_missing_tax_total():
    response = client.post("/validate", json={
        "invoice_xml": VALID_UBL_XML,
        "ruleset": "peppol"
    })
    assert response.status_code == 200
    data = response.json()
    assert any("TaxTotal" in e["description"] for e in data["errors"])


# -------------------------------------------------------
# POST /validate — Australian ruleset
# -------------------------------------------------------
def test_validate_australian_ruleset():
    response = client.post("/validate", json={
        "invoice_xml": VALID_UBL_XML,
        "ruleset": "australian"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ruleset"] == "australian"
    assert isinstance(data["errors"], list)


def test_validate_australian_missing_abn():
    response = client.post("/validate", json={
        "invoice_xml": VALID_UBL_XML,
        "ruleset": "australian"
    })
    assert response.status_code == 200
    data = response.json()
    assert any("ABN" in e["description"] for e in data["errors"])


# -------------------------------------------------------
# Error cases
# -------------------------------------------------------
def test_validate_unsupported_ruleset():
    response = client.post("/validate", json={
        "invoice_xml": VALID_UBL_XML,
        "ruleset": "invalid_ruleset"
    })
    assert response.status_code == 400
    assert "Unsupported ruleset" in response.json()["detail"]


def test_validate_missing_body():
    response = client.post("/validate", json={})
    assert response.status_code == 422


# -------------------------------------------------------
# GET /validate/rulesets
# -------------------------------------------------------
def test_get_supported_rulesets():
    response = client.get("/validate/rulesets")
    assert response.status_code == 200
    data = response.json()
    assert "rulesets" in data
    assert "ubl" in data["rulesets"]
    assert "peppol" in data["rulesets"]
    assert "australian" in data["rulesets"]


def test_validate_bulk_not_implemented():
    response = client.post("/validate/bulk", json={"invoices": ["<Invoice/>"]})
    assert response.status_code == 501


# -------------------------------------------------------
# Health check
# -------------------------------------------------------
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
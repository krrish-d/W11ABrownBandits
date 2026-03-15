import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SAMPLE_JSON = '{"invoice_number": "INV-001", "issue_date": "2026-03-16", "currency": "AUD", "client_name": "XYZ Pty Ltd", "supplier_name": "ABC Pty Ltd", "subtotal": 100.0, "grand_total": 110.0, "items": [{"description": "Consulting", "quantity": 2, "unit_price": 50.0, "line_total": 100.0}]}'

SAMPLE_CSV = """invoice_number,currency,client_name,due_date,subtotal,grand_total,description,quantity,unit_price,line_total
INV-001,AUD,XYZ Pty Ltd,2026-03-16,100.0,110.0,Consulting,2,50.0,100.0"""

SAMPLE_UBL_XML = """<?xml version='1.0' encoding='UTF-8'?>
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


# -------------------------------------------------------
# JSON → UBL XML
# -------------------------------------------------------
def test_endpoint_json_to_ubl_xml():
    response = client.post("/transform/", json={
        "input_format": "json",
        "output_format": "ubl_xml",
        "invoice_data": SAMPLE_JSON
    })
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "Invoice" in response.text


# -------------------------------------------------------
# JSON → CSV
# -------------------------------------------------------
def test_endpoint_json_to_csv():
    response = client.post("/transform/", json={
        "input_format": "json",
        "output_format": "csv",
        "invoice_data": SAMPLE_JSON
    })
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "INV-001" in response.text


# -------------------------------------------------------
# JSON → PDF
# -------------------------------------------------------
def test_endpoint_json_to_pdf():
    response = client.post("/transform/", json={
        "input_format": "json",
        "output_format": "pdf",
        "invoice_data": SAMPLE_JSON
    })
    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert response.content[:4] == b"%PDF"


# -------------------------------------------------------
# CSV → UBL XML
# -------------------------------------------------------
def test_endpoint_csv_to_ubl_xml():
    response = client.post("/transform/", json={
        "input_format": "csv",
        "output_format": "ubl_xml",
        "invoice_data": SAMPLE_CSV
    })
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "Invoice" in response.text


# -------------------------------------------------------
# CSV → JSON
# -------------------------------------------------------
def test_endpoint_csv_to_json():
    response = client.post("/transform/", json={
        "input_format": "csv",
        "output_format": "json",
        "invoice_data": SAMPLE_CSV
    })
    assert response.status_code == 200
    assert "XYZ Pty Ltd" in response.text


# -------------------------------------------------------
# CSV → PDF
# -------------------------------------------------------
def test_endpoint_csv_to_pdf():
    response = client.post("/transform/", json={
        "input_format": "csv",
        "output_format": "pdf",
        "invoice_data": SAMPLE_CSV
    })
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"


# -------------------------------------------------------
# UBL XML → JSON
# -------------------------------------------------------
def test_endpoint_ubl_xml_to_json():
    response = client.post("/transform/", json={
        "input_format": "ubl_xml",
        "output_format": "json",
        "invoice_data": SAMPLE_UBL_XML
    })
    assert response.status_code == 200
    assert "INV-001" in response.text


# -------------------------------------------------------
# UBL XML → CSV
# -------------------------------------------------------
def test_endpoint_ubl_xml_to_csv():
    response = client.post("/transform/", json={
        "input_format": "ubl_xml",
        "output_format": "csv",
        "invoice_data": SAMPLE_UBL_XML
    })
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "INV-001" in response.text


# -------------------------------------------------------
# UBL XML → PDF
# -------------------------------------------------------
def test_endpoint_ubl_xml_to_pdf():
    response = client.post("/transform/", json={
        "input_format": "ubl_xml",
        "output_format": "pdf",
        "invoice_data": SAMPLE_UBL_XML
    })
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"


# -------------------------------------------------------
# Error cases
# -------------------------------------------------------
def test_endpoint_unsupported_input_format():
    response = client.post("/transform/", json={
        "input_format": "pdf",
        "output_format": "json",
        "invoice_data": "data"
    })
    assert response.status_code == 400
    assert "Unsupported input format" in response.json()["detail"]


def test_endpoint_unsupported_output_format():
    response = client.post("/transform/", json={
        "input_format": "json",
        "output_format": "docx",
        "invoice_data": SAMPLE_JSON
    })
    assert response.status_code == 400
    assert "Unsupported output format" in response.json()["detail"]


def test_endpoint_same_format():
    response = client.post("/transform/", json={
        "input_format": "json",
        "output_format": "json",
        "invoice_data": SAMPLE_JSON
    })
    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]


def test_endpoint_invalid_json_input():
    response = client.post("/transform/", json={
        "input_format": "json",
        "output_format": "ubl_xml",
        "invoice_data": "not valid json {{{"
    })
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]


def test_endpoint_invalid_xml_input():
    response = client.post("/transform/", json={
        "input_format": "ubl_xml",
        "output_format": "json",
        "invoice_data": "<not valid xml"
    })
    assert response.status_code == 400
    assert "Invalid XML" in response.json()["detail"]


def test_endpoint_missing_fields():
    response = client.post("/transform/", json={
        "input_format": "json"
    })
    assert response.status_code == 422


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
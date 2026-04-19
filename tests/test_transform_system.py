import base64
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SAMPLE_JSON = '{"invoice_number": "INV-001", "issue_date": "2026-03-16", "currency": "AUD", "buyer_name": "XYZ Pty Ltd", "buyer_address": "2 Buyer Rd, Sydney NSW", "seller_name": "ABC Pty Ltd", "seller_address": "1 Seller St, Melbourne VIC", "subtotal": 100.0, "grand_total": 110.0, "items": [{"item_number": "1", "description": "Consulting", "quantity": 2, "unit_price": 50.0, "line_total": 100.0}]}'

SAMPLE_CSV = """invoice_number,currency,seller_name,seller_address,buyer_name,buyer_address,due_date,subtotal,grand_total,item_number,description,quantity,unit_price,line_total
INV-001,AUD,ABC Pty Ltd,"1 Seller St, Melbourne VIC",XYZ Pty Ltd,"2 Buyer Rd, Sydney NSW",2026-03-16,100.0,110.0,1,Consulting,2,50.0,100.0"""

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
      <cac:PostalAddress>
        <cbc:StreetName>1 Seller St, Melbourne VIC</cbc:StreetName>
      </cac:PostalAddress>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>XYZ Pty Ltd</cbc:Name>
      </cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>2 Buyer Rd, Sydney NSW</cbc:StreetName>
      </cac:PostalAddress>
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

SAMPLE_GENERIC_XML = """<?xml version='1.0' encoding='UTF-8'?>
<Invoice>
  <InvoiceNumber>INV-001</InvoiceNumber>
  <IssueDate>2026-03-16</IssueDate>
  <Currency>AUD</Currency>
  <SellerName>ABC Pty Ltd</SellerName>
  <SellerAddress>1 Seller St, Melbourne VIC</SellerAddress>
  <BuyerName>XYZ Pty Ltd</BuyerName>
  <BuyerAddress>2 Buyer Rd, Sydney NSW</BuyerAddress>
  <Subtotal>100.0</Subtotal>
  <GrandTotal>110.0</GrandTotal>
  <LineItems>
    <LineItem>
      <ItemNumber>1</ItemNumber>
      <Description>Consulting</Description>
      <Quantity>2</Quantity>
      <UnitPrice>50.0</UnitPrice>
      <LineTotal>100.0</LineTotal>
    </LineItem>
  </LineItems>
</Invoice>"""


def make_sample_pdf_b64() -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph("INVOICE", styles["Title"]))
    elements.append(Spacer(1, 5 * mm))
    details = [
        ["Invoice Number:", "INV-001"],
        ["Seller Name:", "ABC Pty Ltd"],
        ["Seller Address:", "1 Seller St, Melbourne VIC"],
        ["Buyer Name:", "XYZ Pty Ltd"],
        ["Buyer Address:", "2 Buyer Rd, Sydney NSW"],
        ["Currency:", "AUD"],
        ["Due Date:", "2026-03-16"],
    ]
    detail_table = Table(details, colWidths=[50 * mm, 120 * mm])
    elements.append(detail_table)
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Line Items", styles["Heading2"]))
    item_data = [
        ["Description", "Quantity", "Unit Price", "Tax Rate", "Line Total"],
        ["Consulting", "2", "AUD 50.00", "10.0%", "AUD 100.00"]
    ]
    item_table = Table(item_data, colWidths=[70 * mm, 25 * mm, 35 * mm, 25 * mm, 35 * mm])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 8 * mm))
    totals = [
        ["Subtotal:", "AUD 100.00"],
        ["Tax Total:", "AUD 10.00"],
        ["Grand Total:", "AUD 110.00"],
    ]
    totals_table = Table(totals, colWidths=[140 * mm, 30 * mm])
    elements.append(totals_table)
    doc.build(elements)
    return base64.b64encode(buffer.getvalue()).decode()


# -------------------------------------------------------
# JSON conversions
# -------------------------------------------------------
def test_endpoint_json_to_ubl_xml():
    response = client.post("/transform", json={"input_format": "json", "output_format": "ubl_xml", "invoice_data": SAMPLE_JSON})
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "Invoice" in response.text

def test_endpoint_json_to_csv():
    response = client.post("/transform", json={"input_format": "json", "output_format": "csv", "invoice_data": SAMPLE_JSON})
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "INV-001" in response.text

def test_endpoint_json_to_xml_ubl():
    response = client.post("/transform", json={"input_format": "json", "output_format": "xml", "invoice_data": SAMPLE_JSON, "xml_type": "ubl"})
    assert response.status_code == 200
    assert "UBLVersionID" in response.text

def test_endpoint_json_to_xml_generic():
    response = client.post("/transform", json={"input_format": "json", "output_format": "xml", "invoice_data": SAMPLE_JSON, "xml_type": "generic"})
    assert response.status_code == 200
    assert "<InvoiceNumber>" in response.text

def test_endpoint_json_to_pdf():
    response = client.post("/transform", json={"input_format": "json", "output_format": "pdf", "invoice_data": SAMPLE_JSON})
    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert response.content[:4] == b"%PDF"


# -------------------------------------------------------
# CSV conversions
# -------------------------------------------------------
def test_endpoint_csv_to_ubl_xml():
    response = client.post("/transform", json={"input_format": "csv", "output_format": "ubl_xml", "invoice_data": SAMPLE_CSV})
    assert response.status_code == 200
    assert "Invoice" in response.text

def test_endpoint_csv_to_json():
    response = client.post("/transform", json={"input_format": "csv", "output_format": "json", "invoice_data": SAMPLE_CSV})
    assert response.status_code == 200
    assert "XYZ Pty Ltd" in response.text

def test_endpoint_csv_to_pdf():
    response = client.post("/transform", json={"input_format": "csv", "output_format": "pdf", "invoice_data": SAMPLE_CSV})
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"


# -------------------------------------------------------
# UBL XML conversions
# -------------------------------------------------------
def test_endpoint_ubl_xml_to_json():
    response = client.post("/transform", json={"input_format": "ubl_xml", "output_format": "json", "invoice_data": SAMPLE_UBL_XML})
    assert response.status_code == 200
    assert "INV-001" in response.text

def test_endpoint_ubl_xml_to_csv():
    response = client.post("/transform", json={"input_format": "ubl_xml", "output_format": "csv", "invoice_data": SAMPLE_UBL_XML})
    assert response.status_code == 200
    assert "INV-001" in response.text

def test_endpoint_ubl_xml_to_pdf():
    response = client.post("/transform", json={"input_format": "ubl_xml", "output_format": "pdf", "invoice_data": SAMPLE_UBL_XML})
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"


# -------------------------------------------------------
# Generic XML conversions
# -------------------------------------------------------
def test_endpoint_generic_xml_to_ubl_xml():
    response = client.post("/transform", json={"input_format": "xml", "output_format": "ubl_xml", "invoice_data": SAMPLE_GENERIC_XML})
    assert response.status_code == 200
    assert "Invoice" in response.text

def test_endpoint_generic_xml_to_json():
    response = client.post("/transform", json={"input_format": "xml", "output_format": "json", "invoice_data": SAMPLE_GENERIC_XML})
    assert response.status_code == 200
    assert "XYZ Pty Ltd" in response.text

def test_endpoint_generic_xml_to_csv():
    response = client.post("/transform", json={"input_format": "xml", "output_format": "csv", "invoice_data": SAMPLE_GENERIC_XML})
    assert response.status_code == 200
    assert "INV-001" in response.text

def test_endpoint_generic_xml_to_pdf():
    response = client.post("/transform", json={"input_format": "xml", "output_format": "pdf", "invoice_data": SAMPLE_GENERIC_XML})
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"


# -------------------------------------------------------
# PDF conversions
# -------------------------------------------------------
def test_endpoint_pdf_to_ubl_xml():
    response = client.post("/transform", json={"input_format": "pdf", "output_format": "ubl_xml", "invoice_data_base64": make_sample_pdf_b64()})
    assert response.status_code == 200
    assert "Invoice" in response.text

def test_endpoint_pdf_to_json():
    response = client.post("/transform", json={"input_format": "pdf", "output_format": "json", "invoice_data_base64": make_sample_pdf_b64()})
    assert response.status_code == 200

def test_endpoint_pdf_to_csv():
    response = client.post("/transform", json={"input_format": "pdf", "output_format": "csv", "invoice_data_base64": make_sample_pdf_b64()})
    assert response.status_code == 200


# -------------------------------------------------------
# Error cases
# -------------------------------------------------------
def test_endpoint_same_format():
    response = client.post("/transform", json={"input_format": "json", "output_format": "json", "invoice_data": SAMPLE_JSON})
    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]

def test_endpoint_unsupported_input_format():
    response = client.post("/transform", json={"input_format": "docx", "output_format": "ubl_xml", "invoice_data": "data"})
    assert response.status_code == 400
    assert "Unsupported input format" in response.json()["detail"]

def test_endpoint_unsupported_output_format():
    response = client.post("/transform", json={"input_format": "json", "output_format": "docx", "invoice_data": SAMPLE_JSON})
    assert response.status_code == 400
    assert "Unsupported output format" in response.json()["detail"]

def test_endpoint_pdf_missing_base64():
    response = client.post("/transform", json={"input_format": "pdf", "output_format": "ubl_xml", "invoice_data": "some data"})
    assert response.status_code == 400
    assert "base64" in response.json()["detail"].lower()

def test_endpoint_pdf_invalid_base64():
    response = client.post("/transform", json={"input_format": "pdf", "output_format": "ubl_xml", "invoice_data_base64": "not-valid-base64!!!"})
    assert response.status_code == 400

def test_endpoint_missing_invoice_data():
    response = client.post("/transform", json={"input_format": "json", "output_format": "ubl_xml"})
    assert response.status_code == 400

def test_endpoint_invalid_json_input():
    response = client.post("/transform", json={"input_format": "json", "output_format": "ubl_xml", "invoice_data": "not valid json {{{"})
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]

def test_endpoint_invalid_xml_input():
    response = client.post("/transform", json={"input_format": "ubl_xml", "output_format": "json", "invoice_data": "<not valid xml"})
    assert response.status_code == 400
    assert "Invalid XML" in response.json()["detail"]

def test_endpoint_missing_fields():
    response = client.post("/transform", json={"input_format": "json"})
    assert response.status_code == 422

def test_endpoint_invalid_xml_type():
    response = client.post("/transform", json={"input_format": "json", "output_format": "xml", "invoice_data": SAMPLE_JSON, "xml_type": "invalid"})
    assert response.status_code == 400
    assert "xml_type" in response.json()["detail"]

def test_endpoint_get_formats():
    response = client.get("/transform/formats")
    assert response.status_code == 200
    data = response.json()
    assert "input_formats" in data
    assert "output_formats" in data
    assert "pdf" in data["input_formats"]
    assert "pdf" in data["output_formats"]

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
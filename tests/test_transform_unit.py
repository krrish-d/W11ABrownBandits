import pytest
from app.services.transform import (
    parse_json,
    parse_csv,
    parse_ubl_xml,
    dict_to_ubl_xml,
    dict_to_json,
    dict_to_csv,
    dict_to_pdf,
    transform,
)

# -------------------------------------------------------
# Sample data reused across tests
# -------------------------------------------------------
SAMPLE_DICT = {
    "invoice_number": "INV-001",
    "issue_date": "2026-03-16",
    "currency": "AUD",
    "client_name": "XYZ Pty Ltd",
    "supplier_name": "ABC Pty Ltd",
    "subtotal": 100.0,
    "grand_total": 110.0,
    "items": [
        {
            "description": "Consulting",
            "quantity": 2,
            "unit_price": 50.0,
            "line_total": 100.0
        }
    ]
}

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
# parse_json
# -------------------------------------------------------
def test_parse_json_valid():
    result = parse_json(SAMPLE_JSON)
    assert result["invoice_number"] == "INV-001"
    assert result["currency"] == "AUD"
    assert len(result["items"]) == 1

def test_parse_json_invalid():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_json("not valid json {{{")


# -------------------------------------------------------
# parse_csv
# -------------------------------------------------------
def test_parse_csv_valid():
    result = parse_csv(SAMPLE_CSV)
    assert result["client_name"] == "XYZ Pty Ltd"
    assert result["currency"] == "AUD"

def test_parse_csv_empty():
    with pytest.raises(ValueError, match="CSV is empty"):
        parse_csv("")

def test_parse_csv_missing_required_field():
    bad_csv = "invoice_number,currency\nINV-001,AUD"
    with pytest.raises(ValueError, match="Missing required CSV field"):
        parse_csv(bad_csv)


# -------------------------------------------------------
# parse_ubl_xml
# -------------------------------------------------------
def test_parse_ubl_xml_valid():
    result = parse_ubl_xml(SAMPLE_UBL_XML)
    assert result["invoice_number"] == "INV-001"
    assert result["currency"] == "AUD"
    assert result["client_name"] == "XYZ Pty Ltd"
    assert result["supplier_name"] == "ABC Pty Ltd"
    assert len(result["items"]) == 1

def test_parse_ubl_xml_invalid():
    with pytest.raises(ValueError, match="Invalid XML"):
        parse_ubl_xml("<not valid xml")


# -------------------------------------------------------
# dict_to_ubl_xml
# -------------------------------------------------------
def test_dict_to_ubl_xml_contains_required_tags():
    result = dict_to_ubl_xml(SAMPLE_DICT)
    assert "<cbc:UBLVersionID>2.1</cbc:UBLVersionID>" in result
    assert "INV-001" in result
    assert "AUD" in result
    assert "Consulting" in result

def test_dict_to_ubl_xml_is_string():
    result = dict_to_ubl_xml(SAMPLE_DICT)
    assert isinstance(result, str)


# -------------------------------------------------------
# dict_to_json
# -------------------------------------------------------
def test_dict_to_json_valid():
    result = dict_to_json(SAMPLE_DICT)
    assert "INV-001" in result
    assert "Consulting" in result

def test_dict_to_json_is_string():
    result = dict_to_json(SAMPLE_DICT)
    assert isinstance(result, str)


# -------------------------------------------------------
# dict_to_csv
# -------------------------------------------------------
def test_dict_to_csv_contains_headers():
    result = dict_to_csv(SAMPLE_DICT)
    assert "invoice_number" in result
    assert "client_name" in result

def test_dict_to_csv_contains_data():
    result = dict_to_csv(SAMPLE_DICT)
    assert "INV-001" in result
    assert "Consulting" in result

def test_dict_to_csv_is_string():
    result = dict_to_csv(SAMPLE_DICT)
    assert isinstance(result, str)


# -------------------------------------------------------
# dict_to_pdf
# -------------------------------------------------------
def test_dict_to_pdf_returns_bytes():
    result = dict_to_pdf(SAMPLE_DICT)
    assert isinstance(result, bytes)

def test_dict_to_pdf_is_pdf_header():
    result = dict_to_pdf(SAMPLE_DICT)
    assert result[:4] == b"%PDF"


# -------------------------------------------------------
# transform (main function)
# -------------------------------------------------------
def test_transform_json_to_ubl_xml():
    result = transform("json", "ubl_xml", SAMPLE_JSON)
    assert "Invoice" in result
    assert "INV-001" in result

def test_transform_json_to_csv():
    result = transform("json", "csv", SAMPLE_JSON)
    assert "INV-001" in result
    assert "invoice_number" in result

def test_transform_json_to_pdf():
    result = transform("json", "pdf", SAMPLE_JSON)
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"

def test_transform_csv_to_ubl_xml():
    result = transform("csv", "ubl_xml", SAMPLE_CSV)
    assert "Invoice" in result

def test_transform_csv_to_json():
    result = transform("csv", "json", SAMPLE_CSV)
    assert "XYZ Pty Ltd" in result

def test_transform_ubl_xml_to_json():
    result = transform("ubl_xml", "json", SAMPLE_UBL_XML)
    assert "INV-001" in result

def test_transform_ubl_xml_to_csv():
    result = transform("ubl_xml", "csv", SAMPLE_UBL_XML)
    assert "INV-001" in result

def test_transform_ubl_xml_to_pdf():
    result = transform("ubl_xml", "pdf", SAMPLE_UBL_XML)
    assert isinstance(result, bytes)

def test_transform_unsupported_input_format():
    with pytest.raises(ValueError, match="Unsupported input format"):
        transform("pdf", "json", "data")

def test_transform_unsupported_output_format():
    with pytest.raises(ValueError, match="Unsupported output format"):
        transform("json", "docx", SAMPLE_JSON)

def test_transform_same_format():
    with pytest.raises(ValueError, match="Input and output formats must be different"):
        transform("json", "json", SAMPLE_JSON)
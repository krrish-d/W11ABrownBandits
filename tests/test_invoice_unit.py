import pytest
from unittest.mock import MagicMock
from app.routers.invoice import generate_ubl_xml, generate_generic_xml, generate_csv, generate_pdf


def make_invoice():
    inv = MagicMock()
    inv.invoice_id = "test-id-123"
    inv.invoice_number = "INV-TESTABCD"
    inv.status = "draft"
    inv.client_name = "Test Client"
    inv.client_email = "test@example.com"
    inv.currency = "AUD"
    inv.due_date = "2026-06-01"
    inv.subtotal = 1000.0
    inv.tax_total = 100.0
    inv.grand_total = 1100.0
    return inv


def make_item():
    item = MagicMock()
    item.item_id = "item-id-456"
    item.description = "Laptop"
    item.quantity = 2.0
    item.unit_price = 500.0
    item.tax_rate = 10.0
    item.line_total = 1000.0
    return item


# UBL XML tests

def test_generate_ubl_xml_returns_string():
    result = generate_ubl_xml(make_invoice(), [make_item()])
    assert isinstance(result, str)

def test_generate_ubl_xml_has_declaration():
    result = generate_ubl_xml(make_invoice(), [make_item()])
    assert "<?xml" in result

def test_generate_ubl_xml_has_version():
    result = generate_ubl_xml(make_invoice(), [make_item()])
    assert "2.1" in result

def test_generate_ubl_xml_has_invoice_number():
    result = generate_ubl_xml(make_invoice(), [make_item()])
    assert "INV-TESTABCD" in result

def test_generate_ubl_xml_has_client_name():
    result = generate_ubl_xml(make_invoice(), [make_item()])
    assert "Test Client" in result

def test_generate_ubl_xml_has_currency():
    result = generate_ubl_xml(make_invoice(), [make_item()])
    assert "AUD" in result

def test_generate_ubl_xml_has_item_description():
    result = generate_ubl_xml(make_invoice(), [make_item()])
    assert "Laptop" in result

def test_generate_ubl_xml_no_items():
    result = generate_ubl_xml(make_invoice(), [])
    assert "Invoice" in result


# Generic XML tests

def test_generate_generic_xml_returns_string():
    result = generate_generic_xml(make_invoice(), [make_item()])
    assert isinstance(result, str)

def test_generate_generic_xml_has_client_name():
    result = generate_generic_xml(make_invoice(), [make_item()])
    assert "Test Client" in result

def test_generate_generic_xml_has_grand_total():
    result = generate_generic_xml(make_invoice(), [make_item()])
    assert "1100.0" in result

def test_generate_generic_xml_has_item():
    result = generate_generic_xml(make_invoice(), [make_item()])
    assert "Laptop" in result

def test_generate_generic_xml_has_invoice_tag():
    result = generate_generic_xml(make_invoice(), [make_item()])
    assert "<Invoice>" in result


# CSV tests

def test_generate_csv_returns_string():
    result = generate_csv(make_invoice(), [make_item()])
    assert isinstance(result, str)

def test_generate_csv_has_header_row():
    result = generate_csv(make_invoice(), [make_item()])
    assert "Invoice ID" in result

def test_generate_csv_has_client_name():
    result = generate_csv(make_invoice(), [make_item()])
    assert "Test Client" in result

def test_generate_csv_has_item_description():
    result = generate_csv(make_invoice(), [make_item()])
    assert "Laptop" in result

def test_generate_csv_has_line_items_header():
    result = generate_csv(make_invoice(), [make_item()])
    assert "Description" in result


# PDF tests

def test_generate_pdf_returns_bytes():
    result = generate_pdf(make_invoice(), [make_item()])
    assert isinstance(result, bytes)

def test_generate_pdf_is_valid_pdf():
    result = generate_pdf(make_invoice(), [make_item()])
    assert result[:4] == b"%PDF"

def test_generate_pdf_no_items():
    result = generate_pdf(make_invoice(), [])
    assert result[:4] == b"%PDF"
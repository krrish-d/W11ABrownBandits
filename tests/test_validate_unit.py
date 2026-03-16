import pytest
from app.services.validate import (
    check_wellformed,
    check_required_fields,
    check_business_rules,
    check_peppol_rules,
    check_australian_rules,
    validate,
)

# -------------------------------------------------------
# Sample data reused across tests
# -------------------------------------------------------
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

INVALID_XML = "<not valid xml"

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
# check_wellformed
# -------------------------------------------------------
def test_wellformed_valid_xml():
    root, errors = check_wellformed(VALID_UBL_XML)
    assert root is not None
    assert errors == []

def test_wellformed_invalid_xml():
    root, errors = check_wellformed(INVALID_XML)
    assert root is None
    assert len(errors) == 1
    assert errors[0]["severity"] == "Critical"
    assert errors[0]["rule"] == "VR2"


# -------------------------------------------------------
# check_required_fields
# -------------------------------------------------------
def test_required_fields_valid():
    from lxml import etree
    root = etree.fromstring(VALID_UBL_XML.encode())
    errors = check_required_fields(root)
    assert errors == []

def test_required_fields_missing():
    from lxml import etree
    root = etree.fromstring(MISSING_FIELDS_XML.encode())
    errors = check_required_fields(root)
    assert len(errors) > 0
    assert all(e["rule"] == "VR3" for e in errors)
    assert all(e["severity"] == "Critical" for e in errors)


# -------------------------------------------------------
# check_business_rules
# -------------------------------------------------------
def test_business_rules_valid():
    from lxml import etree
    root = etree.fromstring(VALID_UBL_XML.encode())
    errors = check_business_rules(root)
    assert errors == []

def test_business_rules_wrong_totals():
    from lxml import etree
    root = etree.fromstring(WRONG_TOTALS_XML.encode())
    errors = check_business_rules(root)
    assert len(errors) > 0
    assert any(e["rule"] == "VR4" for e in errors)

def test_business_rules_invalid_date():
    from lxml import etree
    bad_date_xml = VALID_UBL_XML.replace("2026-03-16", "not-a-date")
    root = etree.fromstring(bad_date_xml.encode())
    errors = check_business_rules(root)
    assert any(e["rule"] == "VR4" and e["severity"] == "Critical" for e in errors)

def test_business_rules_wrong_ubl_version():
    from lxml import etree
    bad_version_xml = VALID_UBL_XML.replace(">2.1<", ">2.0<")
    root = etree.fromstring(bad_version_xml.encode())
    errors = check_business_rules(root)
    assert any(e["rule"] == "VR4" and e["severity"] == "Warning" for e in errors)


# -------------------------------------------------------
# check_peppol_rules
# -------------------------------------------------------
def test_peppol_rules_missing_tax_total():
    from lxml import etree
    root = etree.fromstring(VALID_UBL_XML.encode())
    errors = check_peppol_rules(root)
    assert any(e["rule"] == "VR6" and "TaxTotal" in e["description"] for e in errors)

def test_peppol_rules_missing_party_id():
    from lxml import etree
    root = etree.fromstring(VALID_UBL_XML.encode())
    errors = check_peppol_rules(root)
    assert any(e["rule"] == "VR6" and "Supplier" in e["description"] for e in errors)


# -------------------------------------------------------
# check_australian_rules
# -------------------------------------------------------
def test_australian_rules_missing_abn():
    from lxml import etree
    root = etree.fromstring(VALID_UBL_XML.encode())
    errors = check_australian_rules(root)
    assert any(e["rule"] == "VR7" and "ABN" in e["description"] for e in errors)

def test_australian_rules_non_aud_currency():
    from lxml import etree
    usd_xml = VALID_UBL_XML.replace("AUD", "USD")
    root = etree.fromstring(usd_xml.encode())
    errors = check_australian_rules(root)
    assert any(e["rule"] == "VR7" and "AUD" in e["description"] for e in errors)


# -------------------------------------------------------
# validate (main function)
# -------------------------------------------------------
def test_validate_valid_ubl():
    result = validate(VALID_UBL_XML, "ubl")
    assert result["valid"] is True
    assert result["ruleset"] == "ubl"
    assert isinstance(result["errors"], list)

def test_validate_invalid_xml():
    result = validate(INVALID_XML, "ubl")
    assert result["valid"] is False
    assert len(result["errors"]) > 0

def test_validate_missing_fields():
    result = validate(MISSING_FIELDS_XML, "ubl")
    assert result["valid"] is False

def test_validate_peppol_ruleset():
    result = validate(VALID_UBL_XML, "peppol")
    assert result["ruleset"] == "peppol"
    assert isinstance(result["errors"], list)

def test_validate_australian_ruleset():
    result = validate(VALID_UBL_XML, "australian")
    assert result["ruleset"] == "australian"
    assert isinstance(result["errors"], list)

def test_validate_unsupported_ruleset():
    with pytest.raises(ValueError, match="Unsupported ruleset"):
        validate(VALID_UBL_XML, "invalid_ruleset")

def test_validate_returns_valid_true_for_clean_invoice():
    result = validate(VALID_UBL_XML)
    assert result["valid"] is True

def test_validate_wrong_totals_fails():
    result = validate(WRONG_TOTALS_XML, "ubl")
    assert result["valid"] is False
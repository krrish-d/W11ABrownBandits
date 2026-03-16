from lxml import etree
from datetime import datetime

CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

# -------------------------------------------------------
# HELPER: Get text from a CBC element
# -------------------------------------------------------
def get_cbc(root, tag):
    el = root.find(f"{{{CBC}}}{tag}")
    return el.text if el is not None else None


# -------------------------------------------------------
# VR2: Check XML is well-formed
# -------------------------------------------------------
def check_wellformed(xml_string: str):
    errors = []
    try:
        root = etree.fromstring(xml_string.encode())
        return root, errors
    except etree.XMLSyntaxError as e:
        errors.append({
            "rule": "VR2",
            "severity": "Critical",
            "description": f"XML is not well-formed: {e}"
        })
        return None, errors


# -------------------------------------------------------
# VR3: Check required UBL 2.1 fields are present
# -------------------------------------------------------
def check_required_fields(root) -> list:
    errors = []

    required_cbc_fields = [
        ("UBLVersionID", "UBL Version ID is missing"),
        ("ID", "Invoice ID is missing"),
        ("IssueDate", "Issue Date is missing"),
        ("InvoiceTypeCode", "Invoice Type Code is missing"),
        ("DocumentCurrencyCode", "Document Currency Code is missing"),
    ]

    for tag, message in required_cbc_fields:
        if root.find(f"{{{CBC}}}{tag}") is None:
            errors.append({
                "rule": "VR3",
                "severity": "Critical",
                "description": message
            })

    # Check supplier party
    if root.find(f"{{{CAC}}}AccountingSupplierParty") is None:
        errors.append({
            "rule": "VR3",
            "severity": "Critical",
            "description": "Accounting Supplier Party is missing"
        })

    # Check customer party
    if root.find(f"{{{CAC}}}AccountingCustomerParty") is None:
        errors.append({
            "rule": "VR3",
            "severity": "Critical",
            "description": "Accounting Customer Party is missing"
        })

    # Check legal monetary total
    if root.find(f"{{{CAC}}}LegalMonetaryTotal") is None:
        errors.append({
            "rule": "VR3",
            "severity": "Critical",
            "description": "Legal Monetary Total is missing"
        })

    # Check at least one invoice line
    if not root.findall(f"{{{CAC}}}InvoiceLine"):
        errors.append({
            "rule": "VR3",
            "severity": "Critical",
            "description": "At least one Invoice Line is required"
        })

    return errors


# -------------------------------------------------------
# VR4: Check business rules
# -------------------------------------------------------
def check_business_rules(root) -> list:
    errors = []

    # Check IssueDate is a valid date
    issue_date = get_cbc(root, "IssueDate")
    if issue_date:
        try:
            datetime.strptime(issue_date, "%Y-%m-%d")
        except ValueError:
            errors.append({
                "rule": "VR4",
                "severity": "Critical",
                "description": f"IssueDate '{issue_date}' is not a valid date (expected YYYY-MM-DD)"
            })

    # Check UBL version is 2.1
    ubl_version = get_cbc(root, "UBLVersionID")
    if ubl_version and ubl_version != "2.1":
        errors.append({
            "rule": "VR4",
            "severity": "Warning",
            "description": f"UBLVersionID is '{ubl_version}', expected '2.1'"
        })

    # Check PayableAmount > 0
    monetary = root.find(f"{{{CAC}}}LegalMonetaryTotal")
    if monetary is not None:
        payable_el = monetary.find(f"{{{CBC}}}PayableAmount")
        if payable_el is not None:
            try:
                payable = float(payable_el.text)
                if payable <= 0:
                    errors.append({
                        "rule": "VR4",
                        "severity": "Critical",
                        "description": f"PayableAmount must be greater than 0, got {payable}"
                    })
            except (ValueError, TypeError):
                errors.append({
                    "rule": "VR4",
                    "severity": "Critical",
                    "description": "PayableAmount is not a valid number"
                })

        # Check LineExtensionAmount <= TaxInclusiveAmount
        line_ext_el = monetary.find(f"{{{CBC}}}LineExtensionAmount")
        tax_inc_el = monetary.find(f"{{{CBC}}}TaxInclusiveAmount")
        if line_ext_el is not None and tax_inc_el is not None:
            try:
                line_ext = float(line_ext_el.text)
                tax_inc = float(tax_inc_el.text)
                if line_ext > tax_inc:
                    errors.append({
                        "rule": "VR4",
                        "severity": "Warning",
                        "description": "LineExtensionAmount is greater than TaxInclusiveAmount"
                    })
            except (ValueError, TypeError):
                pass

    # Check line item totals
    invoice_lines = root.findall(f"{{{CAC}}}InvoiceLine")
    calculated_subtotal = 0.0
    for line in invoice_lines:
        qty_el = line.find(f"{{{CBC}}}InvoicedQuantity")
        price_el = line.find(f"{{{CAC}}}Price/{{{CBC}}}PriceAmount")
        line_total_el = line.find(f"{{{CBC}}}LineExtensionAmount")

        if qty_el is not None and price_el is not None and line_total_el is not None:
            try:
                qty = float(qty_el.text)
                price = float(price_el.text)
                line_total = float(line_total_el.text)
                expected_total = round(qty * price, 2)
                if abs(expected_total - line_total) > 0.01:
                    errors.append({
                        "rule": "VR4",
                        "severity": "Critical",
                        "description": f"Line item total mismatch: expected {expected_total}, got {line_total}"
                    })
                calculated_subtotal += line_total
            except (ValueError, TypeError):
                errors.append({
                    "rule": "VR4",
                    "severity": "Critical",
                    "description": "Line item contains non-numeric quantity, price or total"
                })

    # Check calculated subtotal matches LineExtensionAmount in monetary total
    if monetary is not None:
        line_ext_el = monetary.find(f"{{{CBC}}}LineExtensionAmount")
        if line_ext_el is not None:
            try:
                declared_subtotal = float(line_ext_el.text)
                if abs(declared_subtotal - round(calculated_subtotal, 2)) > 0.01:
                    errors.append({
                        "rule": "VR4",
                        "severity": "Critical",
                        "description": f"Subtotal mismatch: line items sum to {round(calculated_subtotal, 2)}, but LineExtensionAmount is {declared_subtotal}"
                    })
            except (ValueError, TypeError):
                pass

    return errors


# -------------------------------------------------------
# VR6: PEPPOL-specific rules
# -------------------------------------------------------
def check_peppol_rules(root) -> list:
    errors = []

    # Supplier must have an ID or endpoint
    supplier = root.find(f"{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party")
    if supplier is not None:
        party_id = supplier.find(f"{{{CAC}}}PartyIdentification/{{{CBC}}}ID")
        endpoint = supplier.find(f"{{{CBC}}}EndpointID")
        if party_id is None and endpoint is None:
            errors.append({
                "rule": "VR6",
                "severity": "Critical",
                "description": "PEPPOL: Supplier Party must have a PartyIdentification ID or EndpointID"
            })

    # Customer must have an ID or endpoint
    customer = root.find(f"{{{CAC}}}AccountingCustomerParty/{{{CAC}}}Party")
    if customer is not None:
        party_id = customer.find(f"{{{CAC}}}PartyIdentification/{{{CBC}}}ID")
        endpoint = customer.find(f"{{{CBC}}}EndpointID")
        if party_id is None and endpoint is None:
            errors.append({
                "rule": "VR6",
                "severity": "Critical",
                "description": "PEPPOL: Customer Party must have a PartyIdentification ID or EndpointID"
            })

    # Must have PaymentMeans
    if root.find(f"{{{CAC}}}PaymentMeans") is None:
        errors.append({
            "rule": "VR6",
            "severity": "Warning",
            "description": "PEPPOL: PaymentMeans is recommended"
        })

    # Must have TaxTotal
    if root.find(f"{{{CAC}}}TaxTotal") is None:
        errors.append({
            "rule": "VR6",
            "severity": "Critical",
            "description": "PEPPOL: TaxTotal is required"
        })

    return errors


# -------------------------------------------------------
# VR7: Australian-specific rules
# -------------------------------------------------------
def check_australian_rules(root) -> list:
    errors = []

    # Currency must be AUD
    currency = get_cbc(root, "DocumentCurrencyCode")
    if currency and currency != "AUD":
        errors.append({
            "rule": "VR7",
            "severity": "Warning",
            "description": f"Australian invoices typically use AUD, got '{currency}'"
        })

    # ABN check - look for PartyTaxScheme/CompanyID
    supplier = root.find(f"{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party")
    if supplier is not None:
        abn_el = supplier.find(f"{{{CAC}}}PartyTaxScheme/{{{CBC}}}CompanyID")
        if abn_el is None:
            errors.append({
                "rule": "VR7",
                "severity": "Warning",
                "description": "Australian invoices should include supplier ABN in PartyTaxScheme/CompanyID"
            })

    # GST - TaxTotal recommended
    if root.find(f"{{{CAC}}}TaxTotal") is None:
        errors.append({
            "rule": "VR7",
            "severity": "Warning",
            "description": "Australian invoices should include TaxTotal for GST reporting"
        })

    return errors


# -------------------------------------------------------
# MAIN: validate(xml_string, ruleset) -> dict
# -------------------------------------------------------
def validate(xml_string: str, ruleset: str = "ubl") -> dict:
    ruleset = ruleset.lower().strip()

    if ruleset not in {"ubl", "peppol", "australian"}:
        raise ValueError(f"Unsupported ruleset: '{ruleset}'. Must be one of: ubl, peppol, australian")

    # VR2: Well-formedness check
    root, errors = check_wellformed(xml_string)
    if root is None:
        return {
            "valid": False,
            "ruleset": ruleset,
            "errors": errors
        }

    # VR3: Required fields
    errors += check_required_fields(root)

    # VR4: Business rules
    errors += check_business_rules(root)

    # VR6: PEPPOL rules
    if ruleset == "peppol":
        errors += check_peppol_rules(root)

    # VR7: Australian rules
    if ruleset == "australian":
        errors += check_australian_rules(root)

    critical_errors = [e for e in errors if e["severity"] == "Critical"]

    return {
        "valid": len(critical_errors) == 0,
        "ruleset": ruleset,
        "errors": errors
    }
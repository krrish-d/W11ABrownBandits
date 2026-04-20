import csv
import io
import json
import re
from lxml import etree


# -------------------------------------------------------
# HELPER: Parse UBL XML string into a plain dict
# -------------------------------------------------------
def parse_ubl_xml(xml_string: str) -> dict:
    try:
        root = etree.fromstring(xml_string.encode())
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML: {e}")

    cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    cac = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

    def get(tag):
        el = root.find(f"{{{cbc}}}{tag}")
        return el.text if el is not None else None

    currency = get("DocumentCurrencyCode") or "AUD"

    def _party_fields(party_path: str):
        name_el = root.find(f"{{{cac}}}{party_path}/{{{cac}}}Party/{{{cac}}}PartyName/{{{cbc}}}Name")
        address_el = root.find(
            f"{{{cac}}}{party_path}/{{{cac}}}Party/{{{cac}}}PostalAddress/{{{cbc}}}StreetName"
        )
        # UBL stores email under Party/Contact/ElectronicMail (or PartyTaxScheme fallback)
        email_el = root.find(
            f"{{{cac}}}{party_path}/{{{cac}}}Party/{{{cac}}}Contact/{{{cbc}}}ElectronicMail"
        )
        return (
            name_el.text if name_el is not None else None,
            address_el.text if address_el is not None else None,
            email_el.text if email_el is not None else None,
        )

    supplier_name, supplier_address, supplier_email = _party_fields("AccountingSupplierParty")
    customer_name, customer_address, customer_email = _party_fields("AccountingCustomerParty")

    monetary = root.find(f"{{{cac}}}LegalMonetaryTotal")
    subtotal = None
    grand_total = None
    if monetary is not None:
        sub_el = monetary.find(f"{{{cbc}}}LineExtensionAmount")
        grand_el = monetary.find(f"{{{cbc}}}PayableAmount")
        subtotal = sub_el.text if sub_el is not None else None
        grand_total = grand_el.text if grand_el is not None else None

    # Root-level TaxTotal (preserve across roundtrips so downstream formats
    # and re-emitted UBL keep a correct tax amount).
    tax_total = None
    tax_total_el = root.find(f"{{{cac}}}TaxTotal/{{{cbc}}}TaxAmount")
    if tax_total_el is not None:
        tax_total = tax_total_el.text

    # Supplier ABN (if present) for roundtrip.
    supplier_abn_el = root.find(
        f"{{{cac}}}AccountingSupplierParty/{{{cac}}}Party/{{{cac}}}PartyTaxScheme/{{{cbc}}}CompanyID"
    )
    supplier_abn = supplier_abn_el.text if supplier_abn_el is not None else None

    items = []
    for line in root.findall(f"{{{cac}}}InvoiceLine"):
        id_el = line.find(f"{{{cbc}}}ID")
        desc_el = line.find(f"{{{cac}}}Item/{{{cbc}}}Description")
        qty_el = line.find(f"{{{cbc}}}InvoicedQuantity")
        total_el = line.find(f"{{{cbc}}}LineExtensionAmount")
        price_el = line.find(f"{{{cac}}}Price/{{{cbc}}}PriceAmount")
        items.append({
            "item_number": id_el.text if id_el is not None else None,
            "description": desc_el.text if desc_el is not None else None,
            "quantity": qty_el.text if qty_el is not None else None,
            "line_total": total_el.text if total_el is not None else None,
            "unit_price": price_el.text if price_el is not None else None,
        })

    return {
        "invoice_number": get("ID"),
        "issue_date": get("IssueDate"),
        "due_date": get("DueDate"),
        "currency": currency,
        "seller_name": supplier_name,
        "seller_address": supplier_address,
        "seller_email": supplier_email,
        "buyer_name": customer_name,
        "buyer_address": customer_address,
        "buyer_email": customer_email,
        "subtotal": subtotal,
        "tax_total": tax_total,
        "grand_total": grand_total,
        "supplier_abn": supplier_abn,
        "items": items
    }


# -------------------------------------------------------
# HELPER: Parse generic XML string into a plain dict
# -------------------------------------------------------
def parse_generic_xml(xml_string: str) -> dict:
    try:
        root = etree.fromstring(xml_string.encode())
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML: {e}")

    def get(tag):
        el = root.find(tag)
        return el.text if el is not None else None

    items = []
    items_el = root.find("LineItems")
    if items_el is not None:
        for item_el in items_el.findall("LineItem"):
            items.append({
                "item_number": item_el.findtext("ItemNumber"),
                "description": item_el.findtext("Description"),
                "quantity": item_el.findtext("Quantity"),
                "unit_price": item_el.findtext("UnitPrice"),
                "tax_rate": item_el.findtext("TaxRate"),
                "line_total": item_el.findtext("LineTotal"),
            })

    return {
        "invoice_number": get("InvoiceNumber"),
        "issue_date": get("IssueDate") or get("DueDate"),
        "due_date": get("DueDate"),
        "currency": get("Currency") or "AUD",
        "buyer_name": get("BuyerName") or get("ClientName"),
        "buyer_address": get("BuyerAddress"),
        "buyer_email": get("BuyerEmail") or get("ClientEmail"),
        "seller_name": get("SellerName") or get("SupplierName"),
        "seller_address": get("SellerAddress"),
        "seller_email": get("SellerEmail") or get("SupplierEmail"),
        "subtotal": get("Subtotal"),
        "grand_total": get("GrandTotal"),
        "items": items
    }


# -------------------------------------------------------
# HELPER: Parse JSON string into a plain dict
# -------------------------------------------------------
def parse_json(json_string: str) -> dict:
    s = json_string.strip()
    try:
        data = json.loads(s)
        # Paste from some UIs wraps JSON as a JSON-encoded string (double-encoded)
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict):
            raise ValueError("JSON must be an object ({ ... }), not an array or primitive")
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


# -------------------------------------------------------
# HELPER: Parse CSV string into a plain dict
# -------------------------------------------------------
# Column names that identify each section of our multi-section CSV format.
_INVOICE_HEADER_KEYS = {"invoice_number", "seller_name", "buyer_name", "currency"}
_ITEM_HEADER_KEYS = {"description", "quantity", "unit_price"}


def parse_csv(csv_string: str) -> dict:
    """
    Parse a CSV that may be in either of the following formats:

    1. Flat layout (all columns on every row, item data duplicated per row)
    2. Multi-section layout produced by our own exporters:

           invoice_number, currency, ... , grand_total
           INV-001,        AUD,     ... , 110.00
           <blank row>
           item_number, description, quantity, unit_price, ...
           1,           Widget,      2,        50,         ...
           2,           Gadget,      1,        10,         ...
    """
    raw_rows = list(csv.reader(io.StringIO(csv_string)))
    if not raw_rows:
        raise ValueError("CSV is empty or missing headers")

    # Drop fully blank rows that might appear at the very top of the file.
    non_empty_rows = [r for r in raw_rows if any(cell.strip() for cell in r)]
    if not non_empty_rows:
        raise ValueError("CSV is empty or missing headers")

    invoice_headers = [h.strip() for h in non_empty_rows[0]]
    invoice_keys = {h.lower() for h in invoice_headers}
    if not invoice_keys.intersection(_INVOICE_HEADER_KEYS):
        raise ValueError(
            "CSV header must include invoice fields such as invoice_number, seller_name, buyer_name."
        )

    # Walk rows after the header, capturing the invoice row and splitting at the item header.
    invoice_row: list[str] | None = None
    item_headers: list[str] | None = None
    item_rows: list[list[str]] = []

    for row in raw_rows[1:]:
        if not any(cell.strip() for cell in row):
            # Blank row signals the boundary between sections.
            continue

        lower_cells = {cell.strip().lower() for cell in row if cell.strip()}

        if item_headers is None and lower_cells.intersection(_ITEM_HEADER_KEYS) and "description" in lower_cells:
            # This row is the line-item header — subsequent rows are items.
            item_headers = [h.strip() for h in row]
            continue

        if item_headers is None:
            # First non-header, non-blank row is the invoice data.
            if invoice_row is None:
                invoice_row = row
            # Ignore any further rows before the item section.
            continue

        item_rows.append(row)

    if invoice_row is None:
        raise ValueError("CSV is missing an invoice data row")

    def _col(row: list[str], headers: list[str], *names: str) -> str:
        for name in names:
            if name in headers:
                idx = headers.index(name)
                if idx < len(row):
                    return (row[idx] or "").strip()
        return ""

    def _col_ci(row: list[str], headers: list[str], *names: str) -> str:
        lowered = [h.lower() for h in headers]
        for name in names:
            name_l = name.lower()
            if name_l in lowered:
                idx = lowered.index(name_l)
                if idx < len(row):
                    return (row[idx] or "").strip()
        return ""

    issue = _col_ci(invoice_row, invoice_headers, "issue_date") or _col_ci(
        invoice_row, invoice_headers, "due_date"
    )
    due = _col_ci(invoice_row, invoice_headers, "due_date") or issue

    required = ["buyer_name", "seller_name", "buyer_address", "seller_address", "currency"]
    for field in required:
        if not _col_ci(invoice_row, invoice_headers, field):
            raise ValueError(f"Missing required CSV field: {field}")

    if not issue:
        raise ValueError("CSV must include 'issue_date' or 'due_date' column with a value")

    items: list[dict] = []
    if item_headers:
        for r in item_rows:
            desc = _col_ci(r, item_headers, "description")
            # Stop if we hit trailing rows that look like totals.
            if not desc:
                continue
            items.append({
                "item_number": _col_ci(r, item_headers, "item_number"),
                "description": desc,
                "quantity": _col_ci(r, item_headers, "quantity"),
                "unit_price": _col_ci(r, item_headers, "unit_price"),
                "tax_rate": _col_ci(r, item_headers, "tax_rate"),
                "line_total": _col_ci(r, item_headers, "line_total"),
            })
    else:
        # Flat CSV — the same row repeats invoice + item information.
        desc = _col_ci(invoice_row, invoice_headers, "description")
        if desc:
            items.append({
                "item_number": _col_ci(invoice_row, invoice_headers, "item_number"),
                "description": desc,
                "quantity": _col_ci(invoice_row, invoice_headers, "quantity"),
                "unit_price": _col_ci(invoice_row, invoice_headers, "unit_price"),
                "tax_rate": _col_ci(invoice_row, invoice_headers, "tax_rate"),
                "line_total": _col_ci(invoice_row, invoice_headers, "line_total"),
            })

    return {
        "invoice_number": _col_ci(invoice_row, invoice_headers, "invoice_number") or None,
        "currency": _col_ci(invoice_row, invoice_headers, "currency"),
        "seller_name": _col_ci(invoice_row, invoice_headers, "seller_name"),
        "seller_address": _col_ci(invoice_row, invoice_headers, "seller_address"),
        "seller_email": _col_ci(invoice_row, invoice_headers, "seller_email") or None,
        "buyer_name": _col_ci(invoice_row, invoice_headers, "buyer_name"),
        "buyer_address": _col_ci(invoice_row, invoice_headers, "buyer_address"),
        "buyer_email": _col_ci(invoice_row, invoice_headers, "buyer_email") or None,
        "issue_date": issue,
        "due_date": due or None,
        "subtotal": _col_ci(invoice_row, invoice_headers, "subtotal") or None,
        "tax_total": _col_ci(invoice_row, invoice_headers, "tax_total") or None,
        "grand_total": _col_ci(invoice_row, invoice_headers, "grand_total") or None,
        "items": items,
    }


# -------------------------------------------------------
# HELPER: Parse PDF bytes into a plain dict
# -------------------------------------------------------
def parse_pdf(pdf_bytes: bytes) -> dict:
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("PDF parsing requires pdfplumber. Run: pip install pdfplumber")

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        tables: list[list[list[str]]] = []
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                tables.append(table)

    if not text.strip():
        raise ValueError("Could not extract text from PDF")

    def extract_field(label):
        # Only match whitespace on the same line so a blank field doesn't
        # swallow the next line's content.
        pattern = rf"{re.escape(label)}[^\S\r\n]*([^\r\n]*)"
        match = re.search(pattern, text)
        if not match:
            return None
        value = match.group(1).strip()
        return value or None

    invoice_number = extract_field("Invoice Number:")
    seller_name = extract_field("Seller Name:") or extract_field("Supplier:")
    seller_address = extract_field("Seller Address:")
    seller_email = extract_field("Seller Email:") or extract_field("Supplier Email:")
    buyer_name = extract_field("Buyer Name:") or extract_field("Client Name:")
    buyer_address = extract_field("Buyer Address:")
    buyer_email = extract_field("Buyer Email:") or extract_field("Client Email:")
    currency_raw = extract_field("Currency:")
    # Prefer explicit Issue Date; fall back to Due Date if the PDF only lists one date.
    issue_date = extract_field("Issue Date:") or extract_field("Due Date:")
    due_date = extract_field("Due Date:") or issue_date
    currency = currency_raw.split()[0] if currency_raw else "AUD"

    subtotal_raw = extract_field("Subtotal:")
    grand_total_raw = extract_field("Grand Total:")

    def clean_amount(val):
        if val is None:
            return None
        parts = val.strip().split()
        return parts[-1] if parts else None

    subtotal = clean_amount(subtotal_raw)
    grand_total = clean_amount(grand_total_raw)

    items: list[dict] = []

    def _clean_cell(value) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split())

    def _strip_currency(value: str) -> str:
        # Remove currency prefixes like "AUD 50.00" / "$50.00" / trailing "%".
        stripped = value.strip().rstrip("%").strip()
        parts = stripped.split()
        return parts[-1] if parts else stripped

    # Prefer the structured tables pdfplumber produces — they handle multi-word
    # descriptions correctly regardless of spacing.
    for table in tables:
        if not table or len(table) < 2:
            continue
        headers = [_clean_cell(c).lower() for c in table[0]]
        if not ("description" in headers and "quantity" in headers):
            continue

        def idx(*names: str) -> int:
            for name in names:
                if name in headers:
                    return headers.index(name)
            return -1

        desc_idx = idx("description")
        qty_idx = idx("quantity")
        price_idx = idx("unit price", "price")
        tax_idx = idx("tax rate", "tax %")
        total_idx = idx("line total", "total")
        num_idx = idx("item #", "item number", "no", "#")

        for row in table[1:]:
            if row is None or all(cell is None or not str(cell).strip() for cell in row):
                continue
            desc = _clean_cell(row[desc_idx]) if 0 <= desc_idx < len(row) else ""
            if not desc:
                continue
            items.append({
                "item_number": _clean_cell(row[num_idx]) if 0 <= num_idx < len(row) else str(len(items) + 1),
                "description": desc,
                "quantity": _clean_cell(row[qty_idx]) if 0 <= qty_idx < len(row) else "",
                "unit_price": _strip_currency(_clean_cell(row[price_idx])) if 0 <= price_idx < len(row) else "",
                "tax_rate": _strip_currency(_clean_cell(row[tax_idx])) if 0 <= tax_idx < len(row) else "",
                "line_total": _strip_currency(_clean_cell(row[total_idx])) if 0 <= total_idx < len(row) else "",
            })
        if items:
            break

    # Fallback: parse the flat text if pdfplumber could not detect a table.
    if not items:
        lines = text.split("\n")
        in_items = False
        header_cols: list[str] = []
        for line in lines:
            lower = line.lower()
            if "description" in lower and "quantity" in lower:
                in_items = True
                header_cols = [c.strip().lower() for c in line.split() if c.strip()]
                continue
            if in_items:
                if "subtotal:" in lower or "tax total:" in lower or "grand total:" in lower:
                    break
                parts = line.strip().split()
                if len(parts) < 4:
                    continue
                # The last 3-4 tokens are numeric (unit price, optional tax %, line total).
                # Detect the number of trailing numeric columns dynamically.
                trailing_numeric = 0
                for token in reversed(parts):
                    if re.fullmatch(r"-?\d+(?:\.\d+)?%?", token):
                        trailing_numeric += 1
                    else:
                        break
                if trailing_numeric < 2:
                    continue

                # Common layouts after `Item# Description ... numbers`:
                #   item_number, description..., quantity, unit_price, line_total (3 trailing)
                #   item_number, description..., quantity, unit_price, tax_rate, line_total (4 trailing)
                if trailing_numeric >= 4:
                    line_total = parts[-1].rstrip("%")
                    tax_rate = parts[-2].rstrip("%")
                    unit_price = parts[-3]
                    quantity = parts[-4]
                    description_tokens = parts[1:-4] if len(parts) > 5 else parts[:-4]
                    item_number = parts[0] if len(parts) > 5 else str(len(items) + 1)
                else:
                    line_total = parts[-1]
                    unit_price = parts[-2]
                    quantity = parts[-3]
                    tax_rate = ""
                    description_tokens = parts[1:-3] if len(parts) > 4 else parts[:-3]
                    item_number = parts[0] if len(parts) > 4 else str(len(items) + 1)

                description = " ".join(description_tokens).strip()
                if not description:
                    continue
                items.append({
                    "item_number": item_number,
                    "description": description,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "tax_rate": tax_rate,
                    "line_total": line_total,
                })

    return {
        "invoice_number": invoice_number,
        "issue_date": issue_date,
        "due_date": due_date,
        "currency": currency,
        "seller_name": seller_name or "Supplier",
        "seller_address": seller_address,
        "seller_email": seller_email,
        "buyer_name": buyer_name,
        "buyer_address": buyer_address,
        "buyer_email": buyer_email,
        "subtotal": subtotal,
        "grand_total": grand_total,
        "items": items
    }


def _require_non_empty(data: dict, field: str, label: str):
    value = data.get(field)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required field: {label}")


def validate_required_fields(data: dict):
    required_pairs = [
        ("seller_name", "seller_name"),
        ("seller_address", "seller_address"),
        ("buyer_name", "buyer_name"),
        ("buyer_address", "buyer_address"),
        ("currency", "currency"),
        ("issue_date", "issue_date"),
    ]
    for field, label in required_pairs:
        _require_non_empty(data, field, label)

    items = data.get("items") or []
    if not items:
        raise ValueError("Missing required field: items (at least one line item required)")

    for idx, item in enumerate(items, start=1):
        for field in ["item_number", "description", "quantity", "unit_price"]:
            val = item.get(field)
            if val is None or str(val).strip() == "":
                raise ValueError(f"Missing required line item field: {field} (item {idx})")


# -------------------------------------------------------
# CONVERTER: dict → UBL XML string
# -------------------------------------------------------
def dict_to_ubl_xml(data: dict) -> str:
    """
    Build a UBL 2.1 Invoice from a plain dict, structured so the result
    passes our UBL, PEPPOL, and Australian validation rulesets by default.
    Adds EndpointID, PaymentMeans, TaxTotal and (when configured) supplier
    ABN so transformations produce compliance-ready output.
    """
    import os

    nsmap = {
        None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    }
    cac = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

    root = etree.Element("Invoice", nsmap=nsmap)
    currency = data.get("currency") or "AUD"

    def _as_float(value, default=0.0):
        try:
            return float(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            return default

    etree.SubElement(root, f"{{{cbc}}}UBLVersionID").text = "2.1"
    etree.SubElement(root, f"{{{cbc}}}ID").text = data.get("invoice_number", "UNKNOWN")
    etree.SubElement(root, f"{{{cbc}}}IssueDate").text = str(data.get("issue_date") or data.get("due_date") or "")
    if data.get("due_date"):
        etree.SubElement(root, f"{{{cbc}}}DueDate").text = str(data.get("due_date", ""))
    etree.SubElement(root, f"{{{cbc}}}InvoiceTypeCode").text = "380"
    etree.SubElement(root, f"{{{cbc}}}DocumentCurrencyCode").text = currency

    # ---------------- Supplier party ----------------
    supplier = etree.SubElement(root, f"{{{cac}}}AccountingSupplierParty")
    supplier_party = etree.SubElement(supplier, f"{{{cac}}}Party")
    etree.SubElement(
        supplier_party, f"{{{cbc}}}EndpointID", schemeID="EM"
    ).text = data.get("seller_email") or "unknown@example.com"
    supplier_name_el = etree.SubElement(supplier_party, f"{{{cac}}}PartyName")
    etree.SubElement(supplier_name_el, f"{{{cbc}}}Name").text = data.get("seller_name", "Unknown Supplier")
    supplier_address = etree.SubElement(supplier_party, f"{{{cac}}}PostalAddress")
    etree.SubElement(supplier_address, f"{{{cbc}}}StreetName").text = data.get("seller_address", "")
    country_el = etree.SubElement(supplier_address, f"{{{cac}}}Country")
    etree.SubElement(country_el, f"{{{cbc}}}IdentificationCode").text = "AU" if currency == "AUD" else "XX"
    supplier_abn = os.getenv("DEFAULT_SUPPLIER_ABN", "").strip() or data.get("supplier_abn") or ""
    if supplier_abn:
        tax_scheme_el = etree.SubElement(supplier_party, f"{{{cac}}}PartyTaxScheme")
        etree.SubElement(tax_scheme_el, f"{{{cbc}}}CompanyID").text = str(supplier_abn)
        scheme_inner = etree.SubElement(tax_scheme_el, f"{{{cac}}}TaxScheme")
        etree.SubElement(scheme_inner, f"{{{cbc}}}ID").text = "GST"
    if data.get("seller_email"):
        supplier_contact = etree.SubElement(supplier_party, f"{{{cac}}}Contact")
        etree.SubElement(supplier_contact, f"{{{cbc}}}ElectronicMail").text = data.get("seller_email", "")

    # ---------------- Customer party ----------------
    customer = etree.SubElement(root, f"{{{cac}}}AccountingCustomerParty")
    customer_party = etree.SubElement(customer, f"{{{cac}}}Party")
    etree.SubElement(
        customer_party, f"{{{cbc}}}EndpointID", schemeID="EM"
    ).text = data.get("buyer_email") or "unknown@example.com"
    customer_name_el = etree.SubElement(customer_party, f"{{{cac}}}PartyName")
    etree.SubElement(customer_name_el, f"{{{cbc}}}Name").text = data.get("buyer_name", "Unknown Customer")
    customer_address = etree.SubElement(customer_party, f"{{{cac}}}PostalAddress")
    etree.SubElement(customer_address, f"{{{cbc}}}StreetName").text = data.get("buyer_address", "")
    if data.get("buyer_email"):
        customer_contact = etree.SubElement(customer_party, f"{{{cac}}}Contact")
        etree.SubElement(customer_contact, f"{{{cbc}}}ElectronicMail").text = data.get("buyer_email", "")

    # ---------------- PaymentMeans ----------------
    payment_means = etree.SubElement(root, f"{{{cac}}}PaymentMeans")
    etree.SubElement(payment_means, f"{{{cbc}}}PaymentMeansCode").text = "30"
    if data.get("due_date"):
        etree.SubElement(payment_means, f"{{{cbc}}}PaymentDueDate").text = str(data.get("due_date"))

    # ---------------- TaxTotal ----------------
    subtotal = _as_float(data.get("subtotal"))
    grand_total = _as_float(data.get("grand_total"))
    # Prefer explicit tax_total if supplied; otherwise infer from totals or
    # sum line-level tax. This keeps roundtrips consistent while ensuring
    # the element is always present (PEPPOL-critical / AU GST).
    if data.get("tax_total") not in (None, ""):
        tax_amount = _as_float(data.get("tax_total"))
    else:
        inferred = grand_total - subtotal
        if inferred <= 0:
            inferred = sum(
                _as_float(item.get("line_total")) * _as_float(item.get("tax_rate")) / 100.0
                for item in data.get("items", [])
            )
        tax_amount = inferred if inferred > 0 else 0.0
    tax_total_el = etree.SubElement(root, f"{{{cac}}}TaxTotal")
    etree.SubElement(
        tax_total_el, f"{{{cbc}}}TaxAmount", currencyID=currency
    ).text = f"{tax_amount:.2f}"

    # ---------------- Legal monetary total ----------------
    monetary_total = etree.SubElement(root, f"{{{cac}}}LegalMonetaryTotal")
    etree.SubElement(monetary_total, f"{{{cbc}}}LineExtensionAmount", currencyID=currency).text = f"{subtotal:.2f}"
    etree.SubElement(monetary_total, f"{{{cbc}}}TaxInclusiveAmount", currencyID=currency).text = f"{grand_total:.2f}"
    etree.SubElement(monetary_total, f"{{{cbc}}}PayableAmount", currencyID=currency).text = f"{grand_total:.2f}"

    # ---------------- Invoice lines ----------------
    for item in data.get("items", []):
        line = etree.SubElement(root, f"{{{cac}}}InvoiceLine")
        etree.SubElement(line, f"{{{cbc}}}ID").text = str(item.get("item_number", "1"))
        etree.SubElement(line, f"{{{cbc}}}InvoicedQuantity", unitCode="EA").text = str(item.get("quantity", 1))
        etree.SubElement(line, f"{{{cbc}}}LineExtensionAmount", currencyID=currency).text = f"{_as_float(item.get('line_total')):.2f}"
        item_el = etree.SubElement(line, f"{{{cac}}}Item")
        etree.SubElement(item_el, f"{{{cbc}}}Description").text = item.get("description", "")
        price_el = etree.SubElement(line, f"{{{cac}}}Price")
        etree.SubElement(price_el, f"{{{cbc}}}PriceAmount", currencyID=currency).text = f"{_as_float(item.get('unit_price')):.2f}"

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


# -------------------------------------------------------
# CONVERTER: dict → Generic XML string
# -------------------------------------------------------
def dict_to_generic_xml(data: dict) -> str:
    root = etree.Element("Invoice")

    etree.SubElement(root, "InvoiceNumber").text = data.get("invoice_number", "")
    etree.SubElement(root, "IssueDate").text = data.get("issue_date", "")
    if data.get("due_date"):
        etree.SubElement(root, "DueDate").text = str(data.get("due_date", ""))
    etree.SubElement(root, "Currency").text = data.get("currency", "AUD")
    etree.SubElement(root, "SellerName").text = data.get("seller_name", "")
    etree.SubElement(root, "SellerAddress").text = data.get("seller_address", "")
    etree.SubElement(root, "SellerEmail").text = data.get("seller_email", "") or ""
    etree.SubElement(root, "BuyerName").text = data.get("buyer_name", "")
    etree.SubElement(root, "BuyerAddress").text = data.get("buyer_address", "")
    etree.SubElement(root, "BuyerEmail").text = data.get("buyer_email", "") or ""
    etree.SubElement(root, "Subtotal").text = str(data.get("subtotal", 0))
    etree.SubElement(root, "GrandTotal").text = str(data.get("grand_total", 0))

    items_el = etree.SubElement(root, "LineItems")
    for item in data.get("items", []):
        item_el = etree.SubElement(items_el, "LineItem")
        etree.SubElement(item_el, "ItemNumber").text = str(item.get("item_number", ""))
        etree.SubElement(item_el, "Description").text = item.get("description", "")
        etree.SubElement(item_el, "Quantity").text = str(item.get("quantity", ""))
        etree.SubElement(item_el, "UnitPrice").text = str(item.get("unit_price", ""))
        etree.SubElement(item_el, "LineTotal").text = str(item.get("line_total", ""))

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


# -------------------------------------------------------
# CONVERTER: dict → JSON string
# -------------------------------------------------------
def dict_to_json(data: dict) -> str:
    return json.dumps(data, indent=2)


# -------------------------------------------------------
# CONVERTER: dict → CSV string
# -------------------------------------------------------
def dict_to_csv(data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "invoice_number", "currency", "seller_name", "seller_address", "seller_email",
            "buyer_name", "buyer_address", "buyer_email",
            "issue_date", "due_date", "subtotal", "grand_total"
        ]
    )
    writer.writerow([
        data.get("invoice_number", ""),
        data.get("currency", ""),
        data.get("seller_name", ""),
        data.get("seller_address", ""),
        data.get("seller_email", "") or "",
        data.get("buyer_name", ""),
        data.get("buyer_address", ""),
        data.get("buyer_email", "") or "",
        data.get("issue_date", ""),
        data.get("due_date", "") or "",
        data.get("subtotal", ""),
        data.get("grand_total", ""),
    ])

    writer.writerow([])
    writer.writerow(["item_number", "description", "quantity", "unit_price", "tax_rate", "line_total"])
    for item in data.get("items", []):
        writer.writerow([
            item.get("item_number", ""),
            item.get("description", ""),
            item.get("quantity", ""),
            item.get("unit_price", ""),
            item.get("tax_rate", "") or "",
            item.get("line_total", ""),
        ])

    return output.getvalue()


# -------------------------------------------------------
# CONVERTER: dict → PDF bytes
# -------------------------------------------------------
def dict_to_pdf(data: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
    except ImportError:
        raise ValueError("PDF generation requires reportlab. Run: pip install reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("INVOICE", styles["Title"]))
    elements.append(Spacer(1, 5 * mm))

    details = [
        ["Invoice Number:", data.get("invoice_number", "")],
        ["Seller Name:", data.get("seller_name", "")],
        ["Seller Address:", data.get("seller_address", "")],
        ["Seller Email:", data.get("seller_email", "") or ""],
        ["Buyer Name:", data.get("buyer_name", "")],
        ["Buyer Address:", data.get("buyer_address", "")],
        ["Buyer Email:", data.get("buyer_email", "") or ""],
        ["Currency:", data.get("currency", "")],
        ["Issue Date:", data.get("issue_date", "")],
        ["Due Date:", str(data.get("due_date", "") or "")],
    ]
    detail_table = Table(details, colWidths=[50 * mm, 120 * mm])
    detail_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 8 * mm))

    elements.append(Paragraph("Line Items", styles["Heading2"]))
    item_data = [["Item #", "Description", "Quantity", "Unit Price", "Line Total"]]
    for item in data.get("items", []):
        item_data.append([
            str(item.get("item_number", "")),
            item.get("description", ""),
            str(item.get("quantity", "")),
            str(item.get("unit_price", "")),
            str(item.get("line_total", "")),
        ])

    item_table = Table(item_data, colWidths=[25 * mm, 55 * mm, 20 * mm, 30 * mm, 30 * mm])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 8 * mm))

    totals = [
        ["Subtotal:", str(data.get("subtotal", ""))],
        ["Grand Total:", str(data.get("grand_total", ""))],
    ]
    totals_table = Table(totals, colWidths=[140 * mm, 30 * mm])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)

    doc.build(elements)
    return buffer.getvalue()


# -------------------------------------------------------
# MAIN: transform(input_format, output_format, data)
# -------------------------------------------------------
SUPPORTED_FORMATS = {"json", "csv", "xml", "ubl_xml", "pdf"}

def transform(input_format: str, output_format: str, invoice_data, xml_type: str = "ubl"):
    input_format = input_format.lower().strip()
    output_format = output_format.lower().strip()
    xml_type = xml_type.lower().strip() if xml_type else "ubl"

    if input_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported input format: '{input_format}'. Must be one of: json, csv, xml, ubl_xml, pdf")

    if output_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported output format: '{output_format}'. Must be one of: json, csv, xml, ubl_xml, pdf")

    if input_format == output_format:
        raise ValueError("Input and output formats must be different")

    if output_format == "xml" and xml_type not in {"ubl", "generic"}:
        raise ValueError("xml_type must be either 'ubl' or 'generic'")

    # Parse input into intermediate dict
    if input_format == "json":
        data = parse_json(invoice_data)
    elif input_format == "csv":
        data = parse_csv(invoice_data)
    elif input_format == "ubl_xml":
        data = parse_ubl_xml(invoice_data)
    elif input_format == "xml":
        data = parse_generic_xml(invoice_data)
    elif input_format == "pdf":
        if isinstance(invoice_data, str):
            raise ValueError("PDF input must be provided as base64-encoded bytes")
        data = parse_pdf(invoice_data)

    validate_required_fields(data)

    # Convert dict to output format
    if output_format == "ubl_xml":
        return dict_to_ubl_xml(data)
    elif output_format == "xml":
        if xml_type == "generic":
            return dict_to_generic_xml(data)
        else:
            return dict_to_ubl_xml(data)
    elif output_format == "json":
        return dict_to_json(data)
    elif output_format == "csv":
        return dict_to_csv(data)
    elif output_format == "pdf":
        return dict_to_pdf(data)

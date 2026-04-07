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

    supplier_name = None
    supplier_el = root.find(f"{{{cac}}}AccountingSupplierParty/{{{cac}}}Party/{{{cac}}}PartyName/{{{cbc}}}Name")
    if supplier_el is not None:
        supplier_name = supplier_el.text
    supplier_address_el = root.find(
        f"{{{cac}}}AccountingSupplierParty/{{{cac}}}Party/{{{cac}}}PostalAddress/{{{cbc}}}StreetName"
    )
    supplier_address = supplier_address_el.text if supplier_address_el is not None else None

    customer_name = None
    customer_el = root.find(f"{{{cac}}}AccountingCustomerParty/{{{cac}}}Party/{{{cac}}}PartyName/{{{cbc}}}Name")
    if customer_el is not None:
        customer_name = customer_el.text
    customer_address_el = root.find(
        f"{{{cac}}}AccountingCustomerParty/{{{cac}}}Party/{{{cac}}}PostalAddress/{{{cbc}}}StreetName"
    )
    customer_address = customer_address_el.text if customer_address_el is not None else None

    monetary = root.find(f"{{{cac}}}LegalMonetaryTotal")
    subtotal = None
    grand_total = None
    if monetary is not None:
        sub_el = monetary.find(f"{{{cbc}}}LineExtensionAmount")
        grand_el = monetary.find(f"{{{cbc}}}PayableAmount")
        subtotal = sub_el.text if sub_el is not None else None
        grand_total = grand_el.text if grand_el is not None else None

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
        "currency": currency,
        "seller_name": supplier_name,
        "seller_address": supplier_address,
        "buyer_name": customer_name,
        "buyer_address": customer_address,
        "subtotal": subtotal,
        "grand_total": grand_total,
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
                "line_total": item_el.findtext("LineTotal"),
            })

    return {
        "invoice_number": get("InvoiceNumber"),
        "issue_date": get("IssueDate") or get("DueDate"),
        "currency": get("Currency") or "AUD",
        "buyer_name": get("BuyerName") or get("ClientName"),
        "buyer_address": get("BuyerAddress"),
        "seller_name": get("SellerName") or get("SupplierName"),
        "seller_address": get("SellerAddress"),
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
        return normalize_invoice_data(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


# -------------------------------------------------------
# HELPER: Parse CSV string into a plain dict
# -------------------------------------------------------
def parse_csv(csv_string: str) -> dict:
    rows_raw = list(csv.reader(io.StringIO(csv_string)))
    if not rows_raw:
        raise ValueError("CSV is empty or missing headers")
    normalized_rows = [[(cell or "").strip() for cell in row] for row in rows_raw]
    non_empty_rows = [row for row in normalized_rows if any(cell for cell in row)]
    if not non_empty_rows:
        raise ValueError("CSV is empty or missing headers")

    def norm_header(value: str) -> str:
        return value.strip().lower().replace(" ", "_").replace("(%)", "").replace("%", "")

    header = [norm_header(h) for h in non_empty_rows[0]]

    # Single-table CSV (legacy/tests): all invoice + item columns on one row.
    if "description" in header and "buyer_name" in header:
        reader = csv.DictReader(io.StringIO(csv_string))
        rows = list(reader)
        row = rows[0] if rows else {}
        items = []
        for r in rows:
            if r.get("description"):
                items.append({
                    "item_number": r.get("item_number"),
                    "description": r.get("description"),
                    "quantity": r.get("quantity"),
                    "unit_price": r.get("unit_price"),
                    "line_total": r.get("line_total"),
                })
        parsed = normalize_invoice_data({
            "invoice_number": row.get("invoice_number"),
            "currency": row.get("currency"),
            "seller_name": row.get("seller_name"),
            "seller_address": row.get("seller_address"),
            "buyer_name": row.get("buyer_name"),
            "buyer_address": row.get("buyer_address"),
            "issue_date": row.get("issue_date") or row.get("due_date"),
            "subtotal": row.get("subtotal"),
            "grand_total": row.get("grand_total"),
            "items": items,
        })
        _validate_csv_required_fields(parsed)
        return parsed

    # Two-section CSV (current generators): first section invoice details, second section line items.
    if len(non_empty_rows) < 2:
        raise ValueError("CSV is missing invoice data row")

    invoice_headers = [norm_header(h) for h in non_empty_rows[0]]
    invoice_values = non_empty_rows[1]
    invoice_data = {invoice_headers[i]: (invoice_values[i] if i < len(invoice_values) else "") for i in range(len(invoice_headers))}

    item_header_idx = None
    for idx in range(2, len(non_empty_rows)):
        hdr = [norm_header(h) for h in non_empty_rows[idx]]
        if "description" in hdr and ("item_number" in hdr or "item_#" in hdr):
            item_header_idx = idx
            break

    items = []
    if item_header_idx is not None:
        item_headers = [norm_header(h).replace("item_#", "item_number").replace("tax_rate_", "tax_rate") for h in non_empty_rows[item_header_idx]]
        for idx in range(item_header_idx + 1, len(non_empty_rows)):
            values = non_empty_rows[idx]
            row = {item_headers[i]: (values[i] if i < len(values) else "") for i in range(len(item_headers))}
            if row.get("description"):
                items.append({
                    "item_number": row.get("item_number"),
                    "description": row.get("description"),
                    "quantity": row.get("quantity"),
                    "unit_price": row.get("unit_price"),
                    "line_total": row.get("line_total"),
                })

    parsed = normalize_invoice_data({
        "invoice_number": invoice_data.get("invoice_number"),
        "currency": invoice_data.get("currency"),
        "seller_name": invoice_data.get("seller_name"),
        "seller_address": invoice_data.get("seller_address"),
        "buyer_name": invoice_data.get("buyer_name"),
        "buyer_address": invoice_data.get("buyer_address"),
        "issue_date": invoice_data.get("issue_date") or invoice_data.get("due_date"),
        "subtotal": invoice_data.get("subtotal"),
        "grand_total": invoice_data.get("grand_total"),
        "items": items,
    })
    _validate_csv_required_fields(parsed)
    return parsed


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

    if not text.strip():
        raise ValueError("Could not extract text from PDF")

    def extract_field(label):
        pattern = rf"{re.escape(label)}\s*([^\n]+)"
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    invoice_number = extract_field("Invoice Number:")
    seller_name = extract_field("Seller Name:") or extract_field("Supplier:")
    seller_address = extract_field("Seller Address:")
    buyer_name = extract_field("Buyer Name:") or extract_field("Client Name:")
    buyer_address = extract_field("Buyer Address:")
    currency_raw = extract_field("Currency:")
    issue_date = extract_field("Due Date:")
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

    items = []
    lines = text.split("\n")
    in_items = False
    for line in lines:
        if "Description" in line and "Quantity" in line:
            in_items = True
            continue
        if in_items:
            if "Subtotal:" in line or "Tax Total:" in line or "Grand Total:" in line:
                break
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    line_total = parts[-1]
                    unit_price = parts[-2]
                    quantity = parts[-4]
                    description = " ".join(parts[:-4])
                    items.append({
                        "item_number": str(len(items) + 1),
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    })
                except (IndexError, ValueError):
                    continue

    return {
        "invoice_number": invoice_number,
        "issue_date": issue_date,
        "currency": currency,
        "seller_name": seller_name or "Supplier",
        "seller_address": seller_address,
        "buyer_name": buyer_name,
        "buyer_address": buyer_address,
        "subtotal": subtotal,
        "grand_total": grand_total,
        "items": items
    }


def _require_non_empty(data: dict, field: str, label: str):
    value = data.get(field)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required field: {label}")


def _to_float(value, default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _validate_csv_required_fields(data: dict):
    if not str(data.get("issue_date") or "").strip():
        raise ValueError("CSV must include 'due_date' or 'issue_date' (and values)")
    for field in ["buyer_name", "seller_name", "buyer_address", "seller_address", "currency"]:
        if not str(data.get(field) or "").strip():
            raise ValueError(f"Missing required CSV field: {field}")


def normalize_invoice_data(data: dict) -> dict:
    seller = data.get("seller_details") if isinstance(data.get("seller_details"), dict) else {}
    buyer = data.get("buyer_details") if isinstance(data.get("buyer_details"), dict) else {}

    items = []
    for idx, item in enumerate(data.get("items") or [], start=1):
        if not isinstance(item, dict):
            continue
        qty = _to_float(item.get("quantity"), 0.0)
        unit_price = _to_float(item.get("unit_price"), 0.0)
        line_total = item.get("line_total")
        if line_total is None or str(line_total).strip() == "":
            line_total = round(qty * unit_price, 2)
        items.append({
            "item_number": item.get("item_number") or str(idx),
            "description": item.get("description", ""),
            "quantity": item.get("quantity"),
            "unit_price": item.get("unit_price"),
            "line_total": line_total,
        })

    subtotal = data.get("subtotal")
    if subtotal is None and items:
        subtotal = round(sum(_to_float(item.get("line_total"), 0.0) for item in items), 2)

    grand_total = data.get("grand_total")
    if grand_total is None:
        grand_total = subtotal

    return {
        "invoice_number": data.get("invoice_number") or data.get("invoice_id") or data.get("id"),
        "issue_date": data.get("issue_date") or data.get("due_date"),
        "currency": data.get("currency"),
        "seller_name": data.get("seller_name") or seller.get("seller_name") or seller.get("name"),
        "seller_address": data.get("seller_address") or seller.get("seller_address") or seller.get("address"),
        "buyer_name": data.get("buyer_name") or data.get("client_name") or buyer.get("buyer_name") or buyer.get("name"),
        "buyer_address": data.get("buyer_address") or buyer.get("buyer_address") or buyer.get("address"),
        "subtotal": subtotal,
        "grand_total": grand_total,
        "items": items,
    }


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
    nsmap = {
        None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    }
    cac = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

    root = etree.Element("Invoice", nsmap=nsmap)

    etree.SubElement(root, f"{{{cbc}}}UBLVersionID").text = "2.1"
    etree.SubElement(root, f"{{{cbc}}}ID").text = data.get("invoice_number", "UNKNOWN")
    etree.SubElement(root, f"{{{cbc}}}IssueDate").text = data.get("issue_date", "")
    etree.SubElement(root, f"{{{cbc}}}InvoiceTypeCode").text = "380"
    etree.SubElement(root, f"{{{cbc}}}DocumentCurrencyCode").text = data.get("currency", "AUD")

    supplier = etree.SubElement(root, f"{{{cac}}}AccountingSupplierParty")
    supplier_party = etree.SubElement(supplier, f"{{{cac}}}Party")
    supplier_name_el = etree.SubElement(supplier_party, f"{{{cac}}}PartyName")
    etree.SubElement(supplier_name_el, f"{{{cbc}}}Name").text = data.get("seller_name", "Unknown Supplier")
    supplier_address = etree.SubElement(supplier_party, f"{{{cac}}}PostalAddress")
    etree.SubElement(supplier_address, f"{{{cbc}}}StreetName").text = data.get("seller_address", "")

    customer = etree.SubElement(root, f"{{{cac}}}AccountingCustomerParty")
    customer_party = etree.SubElement(customer, f"{{{cac}}}Party")
    customer_name_el = etree.SubElement(customer_party, f"{{{cac}}}PartyName")
    etree.SubElement(customer_name_el, f"{{{cbc}}}Name").text = data.get("buyer_name", "Unknown Customer")
    customer_address = etree.SubElement(customer_party, f"{{{cac}}}PostalAddress")
    etree.SubElement(customer_address, f"{{{cbc}}}StreetName").text = data.get("buyer_address", "")

    currency = data.get("currency", "AUD")
    monetary_total = etree.SubElement(root, f"{{{cac}}}LegalMonetaryTotal")
    etree.SubElement(monetary_total, f"{{{cbc}}}LineExtensionAmount", currencyID=currency).text = str(data.get("subtotal", 0))
    etree.SubElement(monetary_total, f"{{{cbc}}}TaxInclusiveAmount", currencyID=currency).text = str(data.get("grand_total", 0))
    etree.SubElement(monetary_total, f"{{{cbc}}}PayableAmount", currencyID=currency).text = str(data.get("grand_total", 0))

    for item in data.get("items", []):
        line = etree.SubElement(root, f"{{{cac}}}InvoiceLine")
        etree.SubElement(line, f"{{{cbc}}}ID").text = str(item.get("item_number", "1"))
        etree.SubElement(line, f"{{{cbc}}}InvoicedQuantity", unitCode="EA").text = str(item.get("quantity", 1))
        etree.SubElement(line, f"{{{cbc}}}LineExtensionAmount", currencyID=currency).text = str(item.get("line_total", 0))
        item_el = etree.SubElement(line, f"{{{cac}}}Item")
        etree.SubElement(item_el, f"{{{cbc}}}Description").text = item.get("description", "")
        price_el = etree.SubElement(line, f"{{{cac}}}Price")
        etree.SubElement(price_el, f"{{{cbc}}}PriceAmount", currencyID=currency).text = str(item.get("unit_price", 0))

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


# -------------------------------------------------------
# CONVERTER: dict → Generic XML string
# -------------------------------------------------------
def dict_to_generic_xml(data: dict) -> str:
    root = etree.Element("Invoice")

    etree.SubElement(root, "InvoiceNumber").text = data.get("invoice_number", "")
    etree.SubElement(root, "IssueDate").text = data.get("issue_date", "")
    etree.SubElement(root, "Currency").text = data.get("currency", "AUD")
    etree.SubElement(root, "SellerName").text = data.get("seller_name", "")
    etree.SubElement(root, "SellerAddress").text = data.get("seller_address", "")
    etree.SubElement(root, "BuyerName").text = data.get("buyer_name", "")
    etree.SubElement(root, "BuyerAddress").text = data.get("buyer_address", "")
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
            "invoice_number", "currency", "seller_name", "seller_address",
            "buyer_name", "buyer_address", "issue_date", "subtotal", "grand_total"
        ]
    )
    writer.writerow([
        data.get("invoice_number", ""),
        data.get("currency", ""),
        data.get("seller_name", ""),
        data.get("seller_address", ""),
        data.get("buyer_name", ""),
        data.get("buyer_address", ""),
        data.get("issue_date", ""),
        data.get("subtotal", ""),
        data.get("grand_total", ""),
    ])

    writer.writerow([])
    writer.writerow(["item_number", "description", "quantity", "unit_price", "line_total"])
    for item in data.get("items", []):
        writer.writerow([
            item.get("item_number", ""),
            item.get("description", ""),
            item.get("quantity", ""),
            item.get("unit_price", ""),
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
        ["Buyer Name:", data.get("buyer_name", "")],
        ["Buyer Address:", data.get("buyer_address", "")],
        ["Currency:", data.get("currency", "")],
        ["Issue Date:", data.get("issue_date", "")],
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

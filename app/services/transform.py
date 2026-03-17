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

    customer_name = None
    customer_el = root.find(f"{{{cac}}}AccountingCustomerParty/{{{cac}}}Party/{{{cac}}}PartyName/{{{cbc}}}Name")
    if customer_el is not None:
        customer_name = customer_el.text

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
        desc_el = line.find(f"{{{cac}}}Item/{{{cbc}}}Description")
        qty_el = line.find(f"{{{cbc}}}InvoicedQuantity")
        total_el = line.find(f"{{{cbc}}}LineExtensionAmount")
        price_el = line.find(f"{{{cac}}}Price/{{{cbc}}}PriceAmount")
        items.append({
            "description": desc_el.text if desc_el is not None else None,
            "quantity": qty_el.text if qty_el is not None else None,
            "line_total": total_el.text if total_el is not None else None,
            "unit_price": price_el.text if price_el is not None else None,
        })

    return {
        "invoice_number": get("ID"),
        "issue_date": get("IssueDate"),
        "currency": currency,
        "supplier_name": supplier_name,
        "client_name": customer_name,
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
                "description": item_el.findtext("Description"),
                "quantity": item_el.findtext("Quantity"),
                "unit_price": item_el.findtext("UnitPrice"),
                "line_total": item_el.findtext("LineTotal"),
            })

    return {
        "invoice_number": get("InvoiceNumber"),
        "issue_date": get("DueDate"),
        "currency": get("Currency") or "AUD",
        "client_name": get("ClientName"),
        "supplier_name": "Supplier",
        "subtotal": get("Subtotal"),
        "grand_total": get("GrandTotal"),
        "items": items
    }


# -------------------------------------------------------
# HELPER: Parse JSON string into a plain dict
# -------------------------------------------------------
def parse_json(json_string: str) -> dict:
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


# -------------------------------------------------------
# HELPER: Parse CSV string into a plain dict
# -------------------------------------------------------
def parse_csv(csv_string: str) -> dict:
    reader = csv.DictReader(io.StringIO(csv_string))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV is empty or missing headers")

    row = rows[0]

    required = ["client_name", "currency", "due_date"]
    for field in required:
        if field not in row or not row[field]:
            raise ValueError(f"Missing required CSV field: {field}")

    items = []
    for r in rows:
        if r.get("description"):
            items.append({
                "description": r.get("description"),
                "quantity": r.get("quantity"),
                "unit_price": r.get("unit_price"),
                "line_total": r.get("line_total"),
            })

    return {
        "invoice_number": row.get("invoice_number"),
        "currency": row["currency"],
        "client_name": row["client_name"],
        "issue_date": row.get("due_date"),
        "items": items
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

    if not text.strip():
        raise ValueError("Could not extract text from PDF")

    def extract_field(label):
        pattern = rf"{re.escape(label)}\s*([^\n]+)"
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    invoice_number = extract_field("Invoice Number:")
    client_name = extract_field("Client Name:")
    currency_raw = extract_field("Currency:")
    issue_date = extract_field("Due Date:")

    # Currency may appear as just "AUD" or with extra text
    currency = currency_raw.split()[0] if currency_raw else "AUD"

    # Extract totals
    subtotal_raw = extract_field("Subtotal:")
    grand_total_raw = extract_field("Grand Total:")

    def clean_amount(val):
        if val is None:
            return None
        # Remove currency prefix e.g. "AUD 100.00" -> "100.00"
        parts = val.strip().split()
        return parts[-1] if parts else None

    subtotal = clean_amount(subtotal_raw)
    grand_total = clean_amount(grand_total_raw)

    # Extract line items from table
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
                    # Last value is line_total, second last is unit_price (with currency), 
                    # third last is tax rate, fourth last is quantity
                    line_total = parts[-1]
                    unit_price = parts[-2]
                    quantity = parts[-4]
                    description = " ".join(parts[:-4])
                    items.append({
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
        "client_name": client_name,
        "supplier_name": "Supplier",
        "subtotal": subtotal,
        "grand_total": grand_total,
        "items": items
    }


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
    etree.SubElement(supplier_name_el, f"{{{cbc}}}Name").text = data.get("supplier_name", "Unknown Supplier")

    customer = etree.SubElement(root, f"{{{cac}}}AccountingCustomerParty")
    customer_party = etree.SubElement(customer, f"{{{cac}}}Party")
    customer_name_el = etree.SubElement(customer_party, f"{{{cac}}}PartyName")
    etree.SubElement(customer_name_el, f"{{{cbc}}}Name").text = data.get("client_name", "Unknown Customer")

    currency = data.get("currency", "AUD")
    monetary_total = etree.SubElement(root, f"{{{cac}}}LegalMonetaryTotal")
    etree.SubElement(monetary_total, f"{{{cbc}}}LineExtensionAmount", currencyID=currency).text = str(data.get("subtotal", 0))
    etree.SubElement(monetary_total, f"{{{cbc}}}TaxInclusiveAmount", currencyID=currency).text = str(data.get("grand_total", 0))
    etree.SubElement(monetary_total, f"{{{cbc}}}PayableAmount", currencyID=currency).text = str(data.get("grand_total", 0))

    for item in data.get("items", []):
        line = etree.SubElement(root, f"{{{cac}}}InvoiceLine")
        etree.SubElement(line, f"{{{cbc}}}ID").text = str(item.get("item_id", "1"))
        etree.SubElement(line, f"{{{cbc}}}InvoicedQuantity", unitCode="EA").text = str(item.get("quantity", 1))
        etree.SubElement(line, f"{{{cbc}}}LineExtensionAmount", currencyID=currency).text = str(item.get("line_total", 0))
        item_el = etree.SubElement(line, f"{{{cac}}}Item")
        etree.SubElement(item_el, f"{{{cbc}}}Description").text = item.get("description", "")
        price_el = etree.SubElement(line, f"{{{cac}}}Price")
        etree.SubElement(price_el, f"{{{cbc}}}PriceAmount", currencyID=currency).text = str(item.get("unit_price", 0))

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


# -------------------------------------------------------
# MAIN: transform(input_format, output_format, data)
# -------------------------------------------------------
SUPPORTED_INPUT_FORMATS = {"json", "csv", "ubl_xml", "xml", "pdf"}

def transform(input_format: str, output_format: str, invoice_data):
    input_format = input_format.lower().strip()
    output_format = output_format.lower().strip()

    if input_format not in SUPPORTED_INPUT_FORMATS:
        raise ValueError(f"Unsupported input format: '{input_format}'. Must be one of: json, csv, xml, ubl_xml, pdf")

    if output_format != "ubl_xml":
        raise ValueError(f"Unsupported output format: '{output_format}'. Only 'ubl_xml' is supported as output.")

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
        # PDF input must be bytes
        if isinstance(invoice_data, str):
            raise ValueError("PDF input must be provided as base64-encoded bytes")
        data = parse_pdf(invoice_data)

    return dict_to_ubl_xml(data)
import csv
import io
import json
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

    # Extract supplier name
    supplier_name = None
    supplier_el = root.find(f"{{{cac}}}AccountingSupplierParty/{{{cac}}}Party/{{{cac}}}PartyName/{{{cbc}}}Name")
    if supplier_el is not None:
        supplier_name = supplier_el.text

    # Extract customer name
    customer_name = None
    customer_el = root.find(f"{{{cac}}}AccountingCustomerParty/{{{cac}}}Party/{{{cac}}}PartyName/{{{cbc}}}Name")
    if customer_el is not None:
        customer_name = customer_el.text

    # Extract totals
    monetary = root.find(f"{{{cac}}}LegalMonetaryTotal")
    subtotal = None
    grand_total = None
    if monetary is not None:
        sub_el = monetary.find(f"{{{cbc}}}LineExtensionAmount")
        grand_el = monetary.find(f"{{{cbc}}}PayableAmount")
        subtotal = sub_el.text if sub_el is not None else None
        grand_total = grand_el.text if grand_el is not None else None

    # Extract line items
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

    # First row has invoice-level fields
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

    writer.writerow(["invoice_number", "currency", "client_name", "supplier_name", "issue_date", "subtotal", "grand_total"])
    writer.writerow([
        data.get("invoice_number", ""),
        data.get("currency", ""),
        data.get("client_name", ""),
        data.get("supplier_name", ""),
        data.get("issue_date", ""),
        data.get("subtotal", ""),
        data.get("grand_total", ""),
    ])

    writer.writerow([])
    writer.writerow(["description", "quantity", "unit_price", "line_total"])
    for item in data.get("items", []):
        writer.writerow([
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
        ["Client Name:", data.get("client_name", "")],
        ["Supplier:", data.get("supplier_name", "")],
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
    item_data = [["Description", "Quantity", "Unit Price", "Line Total"]]
    for item in data.get("items", []):
        item_data.append([
            item.get("description", ""),
            str(item.get("quantity", "")),
            str(item.get("unit_price", "")),
            str(item.get("line_total", "")),
        ])

    item_table = Table(item_data, colWidths=[80 * mm, 25 * mm, 35 * mm, 35 * mm])
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
# MAIN: transform(input_format, output_format, data) -> str | bytes
# -------------------------------------------------------
SUPPORTED_FORMATS = {"json", "csv", "ubl_xml", "pdf"}

def transform(input_format: str, output_format: str, invoice_data: str):
    input_format = input_format.lower().strip()
    output_format = output_format.lower().strip()

    if input_format not in SUPPORTED_FORMATS - {"pdf"}:
        raise ValueError(f"Unsupported input format: '{input_format}'. Must be one of: json, csv, ubl_xml")

    if output_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported output format: '{output_format}'. Must be one of: json, csv, ubl_xml, pdf")

    if input_format == output_format:
        raise ValueError("Input and output formats must be different")

    # Parse input into intermediate dict
    if input_format == "json":
        data = parse_json(invoice_data)
    elif input_format == "csv":
        data = parse_csv(invoice_data)
    elif input_format == "ubl_xml":
        data = parse_ubl_xml(invoice_data)

    # Convert dict to output format
    if output_format == "ubl_xml":
        return dict_to_ubl_xml(data)
    elif output_format == "json":
        return dict_to_json(data)
    elif output_format == "csv":
        return dict_to_csv(data)
    elif output_format == "pdf":
        return dict_to_pdf(data)
import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from lxml import etree
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invoice import Invoice, LineItem
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceUpdate

router = APIRouter(
    prefix="/invoices",
    tags=["Invoice Creation"]
)


def generate_ubl_xml(invoice: Invoice, items: list) -> str:
    nsmap = {
        None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    }
    cac = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

    root = etree.Element("Invoice", nsmap=nsmap)

    etree.SubElement(root, f"{{{cbc}}}UBLVersionID").text = "2.1"
    etree.SubElement(root, f"{{{cbc}}}ID").text = invoice.invoice_number
    etree.SubElement(root, f"{{{cbc}}}IssueDate").text = str(invoice.due_date)
    etree.SubElement(root, f"{{{cbc}}}InvoiceTypeCode").text = "380"
    etree.SubElement(root, f"{{{cbc}}}DocumentCurrencyCode").text = invoice.currency

    supplier = etree.SubElement(root, f"{{{cac}}}AccountingSupplierParty")
    supplier_party = etree.SubElement(supplier, f"{{{cac}}}Party")
    supplier_name_el = etree.SubElement(supplier_party, f"{{{cac}}}PartyName")
    etree.SubElement(supplier_name_el, f"{{{cbc}}}Name").text = "Supplier"

    customer = etree.SubElement(root, f"{{{cac}}}AccountingCustomerParty")
    customer_party = etree.SubElement(customer, f"{{{cac}}}Party")
    customer_name_el = etree.SubElement(customer_party, f"{{{cac}}}PartyName")
    etree.SubElement(customer_name_el, f"{{{cbc}}}Name").text = invoice.client_name

    monetary_total = etree.SubElement(root, f"{{{cac}}}LegalMonetaryTotal")
    etree.SubElement(monetary_total, f"{{{cbc}}}LineExtensionAmount", currencyID=invoice.currency).text = str(invoice.subtotal)
    etree.SubElement(monetary_total, f"{{{cbc}}}TaxInclusiveAmount", currencyID=invoice.currency).text = str(invoice.grand_total)
    etree.SubElement(monetary_total, f"{{{cbc}}}PayableAmount", currencyID=invoice.currency).text = str(invoice.grand_total)

    for item in items:
        line = etree.SubElement(root, f"{{{cac}}}InvoiceLine")
        etree.SubElement(line, f"{{{cbc}}}ID").text = item.item_id
        etree.SubElement(line, f"{{{cbc}}}InvoicedQuantity", unitCode="EA").text = str(item.quantity)
        etree.SubElement(line, f"{{{cbc}}}LineExtensionAmount", currencyID=invoice.currency).text = str(item.line_total)
        item_el = etree.SubElement(line, f"{{{cac}}}Item")
        etree.SubElement(item_el, f"{{{cbc}}}Description").text = item.description
        price_el = etree.SubElement(line, f"{{{cac}}}Price")
        etree.SubElement(price_el, f"{{{cbc}}}PriceAmount", currencyID=invoice.currency).text = str(item.unit_price)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


def generate_generic_xml(invoice: Invoice, items: list) -> str:
    root = etree.Element("Invoice")

    etree.SubElement(root, "InvoiceID").text = invoice.invoice_id
    etree.SubElement(root, "InvoiceNumber").text = invoice.invoice_number
    etree.SubElement(root, "Status").text = invoice.status
    etree.SubElement(root, "ClientName").text = invoice.client_name
    etree.SubElement(root, "ClientEmail").text = invoice.client_email
    etree.SubElement(root, "Currency").text = invoice.currency
    etree.SubElement(root, "DueDate").text = str(invoice.due_date)
    etree.SubElement(root, "Subtotal").text = str(invoice.subtotal)
    etree.SubElement(root, "TaxTotal").text = str(invoice.tax_total)
    etree.SubElement(root, "GrandTotal").text = str(invoice.grand_total)

    items_el = etree.SubElement(root, "LineItems")
    for item in items:
        item_el = etree.SubElement(items_el, "LineItem")
        etree.SubElement(item_el, "Description").text = item.description
        etree.SubElement(item_el, "Quantity").text = str(item.quantity)
        etree.SubElement(item_el, "UnitPrice").text = str(item.unit_price)
        etree.SubElement(item_el, "TaxRate").text = str(item.tax_rate)
        etree.SubElement(item_el, "LineTotal").text = str(item.line_total)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


def generate_csv(invoice: Invoice, items: list) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Invoice ID", "Invoice Number", "Status", "Client Name",
                     "Client Email", "Currency", "Due Date",
                     "Subtotal", "Tax Total", "Grand Total"])
    writer.writerow([
        invoice.invoice_id, invoice.invoice_number, invoice.status,
        invoice.client_name, invoice.client_email, invoice.currency,
        str(invoice.due_date), invoice.subtotal, invoice.tax_total, invoice.grand_total
    ])

    writer.writerow([])
    writer.writerow(["Description", "Quantity", "Unit Price", "Tax Rate (%)", "Line Total"])
    for item in items:
        writer.writerow([
            item.description, item.quantity, item.unit_price,
            item.tax_rate, item.line_total
        ])

    return output.getvalue()


def generate_pdf(invoice: Invoice, items: list) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF generation requires reportlab. Run: pip install reportlab"
        )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("INVOICE", styles["Title"]))
    elements.append(Spacer(1, 5 * mm))

    details = [
        ["Invoice Number:", invoice.invoice_number],
        ["Invoice ID:", invoice.invoice_id],
        ["Client Name:", invoice.client_name],
        ["Client Email:", invoice.client_email],
        ["Currency:", invoice.currency],
        ["Due Date:", str(invoice.due_date)],
        ["Status:", invoice.status],
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
    item_data = [["Description", "Quantity", "Unit Price", "Tax Rate", "Line Total"]]
    for item in items:
        item_data.append([
            item.description,
            str(item.quantity),
            f"{invoice.currency} {item.unit_price:.2f}",
            f"{item.tax_rate}%",
            f"{invoice.currency} {item.line_total:.2f}"
        ])

    item_table = Table(item_data, colWidths=[70 * mm, 25 * mm, 35 * mm, 25 * mm, 35 * mm])
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
        ["Subtotal:", f"{invoice.currency} {invoice.subtotal:.2f}"],
        ["Tax Total:", f"{invoice.currency} {invoice.tax_total:.2f}"],
        ["Grand Total:", f"{invoice.currency} {invoice.grand_total:.2f}"],
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


@router.post("/", response_model=InvoiceResponse, status_code=201)
def create_invoice(invoice_data: InvoiceCreate, db: Session = Depends(get_db)):
    invoice_number = f"INV-{str(uuid.uuid4())[:8].upper()}"

    subtotal = 0.0
    tax_total = 0.0
    line_items_data = []

    for item in invoice_data.items:
        line_total = round(item.quantity * item.unit_price, 2)
        tax_amount = round(line_total * (item.tax_rate / 100), 2)
        subtotal += line_total
        tax_total += tax_amount
        line_items_data.append({
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "tax_rate": item.tax_rate,
            "line_total": line_total
        })

    subtotal = round(subtotal, 2)
    tax_total = round(tax_total, 2)
    grand_total = round(subtotal + tax_total, 2)

    new_invoice = Invoice(
        invoice_number=invoice_number,
        client_name=invoice_data.client_name,
        client_email=invoice_data.client_email,
        currency=invoice_data.currency,
        due_date=invoice_data.due_date,
        notes=invoice_data.notes,
        subtotal=subtotal,
        tax_total=tax_total,
        grand_total=grand_total
    )
    db.add(new_invoice)
    db.flush()

    for item_data in line_items_data:
        line_item = LineItem(invoice_id=new_invoice.invoice_id, **item_data)
        db.add(line_item)

    db.commit()
    db.refresh(new_invoice)
    return new_invoice


@router.get("/", response_model=list[InvoiceResponse])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).all()


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: str,
    format: str = Query(
        default="json",
        description="Output format: json, ubl, xml, csv, pdf"
    ),
    db: Session = Depends(get_db)
):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    items = db.query(LineItem).filter(LineItem.invoice_id == invoice_id).all()

    if format == "ubl":
        content = generate_ubl_xml(invoice, items)
        return Response(content=content, media_type="application/xml")

    elif format == "xml":
        content = generate_generic_xml(invoice, items)
        return Response(content=content, media_type="application/xml")

    elif format == "csv":
        content = generate_csv(invoice, items)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=invoice-{invoice_id}.csv"}
        )

    elif format == "pdf":
        content = generate_pdf(invoice, items)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice-{invoice_id}.pdf"}
        )

    else:
        return InvoiceResponse.model_validate(invoice)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(invoice_id: str, updates: InvoiceUpdate, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)

    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}", status_code=200)
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    db.delete(invoice)
    db.commit()
    return {"message": f"Invoice {invoice_id} deleted successfully"}
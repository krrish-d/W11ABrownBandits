import csv
import io
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from lxml import etree
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invoice import Invoice, LineItem
from app.models.invoice_import import InvoiceImportToken
from app.models.user import User
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceUpdate
from app.services.audit import log_audit
from app.services.auth import get_optional_current_user

router = APIRouter(
    prefix="/invoice",
    tags=["Invoice Creation"]
)

legacy_router = APIRouter(
    prefix="/invoices",
    tags=["Invoice Creation (Legacy)"]
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
    etree.SubElement(supplier_name_el, f"{{{cbc}}}Name").text = invoice.seller_name
    supplier_address = etree.SubElement(supplier_party, f"{{{cac}}}PostalAddress")
    etree.SubElement(supplier_address, f"{{{cbc}}}StreetName").text = invoice.seller_address

    customer = etree.SubElement(root, f"{{{cac}}}AccountingCustomerParty")
    customer_party = etree.SubElement(customer, f"{{{cac}}}Party")
    customer_name_el = etree.SubElement(customer_party, f"{{{cac}}}PartyName")
    etree.SubElement(customer_name_el, f"{{{cbc}}}Name").text = invoice.buyer_name
    customer_address = etree.SubElement(customer_party, f"{{{cac}}}PostalAddress")
    etree.SubElement(customer_address, f"{{{cbc}}}StreetName").text = invoice.buyer_address

    monetary_total = etree.SubElement(root, f"{{{cac}}}LegalMonetaryTotal")
    etree.SubElement(monetary_total, f"{{{cbc}}}LineExtensionAmount", currencyID=invoice.currency).text = str(invoice.subtotal)
    etree.SubElement(monetary_total, f"{{{cbc}}}TaxInclusiveAmount", currencyID=invoice.currency).text = str(invoice.grand_total)
    etree.SubElement(monetary_total, f"{{{cbc}}}PayableAmount", currencyID=invoice.currency).text = str(invoice.grand_total)

    for item in items:
        line = etree.SubElement(root, f"{{{cac}}}InvoiceLine")
        etree.SubElement(line, f"{{{cbc}}}ID").text = item.item_number
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
    etree.SubElement(root, "SellerName").text = invoice.seller_name
    etree.SubElement(root, "SellerAddress").text = invoice.seller_address
    etree.SubElement(root, "SellerEmail").text = invoice.seller_email
    etree.SubElement(root, "BuyerName").text = invoice.buyer_name
    etree.SubElement(root, "BuyerAddress").text = invoice.buyer_address
    etree.SubElement(root, "BuyerEmail").text = invoice.buyer_email
    etree.SubElement(root, "Currency").text = invoice.currency
    etree.SubElement(root, "DueDate").text = str(invoice.due_date)
    etree.SubElement(root, "Subtotal").text = str(invoice.subtotal)
    etree.SubElement(root, "TaxTotal").text = str(invoice.tax_total)
    etree.SubElement(root, "GrandTotal").text = str(invoice.grand_total)

    items_el = etree.SubElement(root, "LineItems")
    for item in items:
        item_el = etree.SubElement(items_el, "LineItem")
        etree.SubElement(item_el, "ItemNumber").text = item.item_number
        etree.SubElement(item_el, "Description").text = item.description
        etree.SubElement(item_el, "Quantity").text = str(item.quantity)
        etree.SubElement(item_el, "UnitPrice").text = str(item.unit_price)
        etree.SubElement(item_el, "TaxRate").text = str(item.tax_rate)
        etree.SubElement(item_el, "LineTotal").text = str(item.line_total)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


def generate_csv(invoice: Invoice, items: list) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Invoice ID", "Invoice Number", "Status", "Seller Name",
                     "Seller Address", "Seller Email", "Buyer Name", "Buyer Address",
                     "Buyer Email", "Currency", "Due Date",
                     "Subtotal", "Tax Total", "Grand Total"])
    writer.writerow([
        invoice.invoice_id, invoice.invoice_number, invoice.status,
        invoice.seller_name, invoice.seller_address, invoice.seller_email,
        invoice.buyer_name, invoice.buyer_address, invoice.buyer_email, invoice.currency,
        str(invoice.due_date), invoice.subtotal, invoice.tax_total, invoice.grand_total
    ])

    writer.writerow([])
    writer.writerow(["Item Number", "Description", "Quantity", "Unit Price", "Tax Rate (%)", "Line Total"])
    for item in items:
        writer.writerow([
            item.item_number, item.description, item.quantity, item.unit_price,
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
        ["Seller Name:", invoice.seller_name],
        ["Seller Address:", invoice.seller_address],
        ["Seller Email:", invoice.seller_email],
        ["Buyer Name:", invoice.buyer_name],
        ["Buyer Address:", invoice.buyer_address],
        ["Buyer Email:", invoice.buyer_email],
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
    item_data = [["Item #", "Description", "Quantity", "Unit Price", "Tax Rate", "Line Total"]]
    for item in items:
        item_data.append([
            item.item_number,
            item.description,
            str(item.quantity),
            f"{invoice.currency} {item.unit_price:.2f}",
            f"{item.tax_rate}%",
            f"{invoice.currency} {item.line_total:.2f}"
        ])

    item_table = Table(item_data, colWidths=[20 * mm, 50 * mm, 20 * mm, 30 * mm, 20 * mm, 30 * mm])
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


def _auto_mark_overdue(db: Session) -> int:
    """Mark all past-due, non-terminal invoices as overdue. Returns count changed."""
    today = date.today()
    candidates = (
        db.query(Invoice)
        .filter(
            Invoice.due_date < today,
            Invoice.status.notin_(["paid", "cancelled", "overdue"]),
        )
        .all()
    )
    for inv in candidates:
        log_audit(db, "invoice", inv.invoice_id, "status_change",
                  changed_by="system",
                  changes={"status": {"old": inv.status, "new": "overdue"}})
        inv.status = "overdue"
    return len(candidates)


@router.post("/create", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    invoice_data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
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
            "item_number": item.item_number,
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
        owner_id=current_user.user_id if current_user else None,
        seller_name=invoice_data.seller_name,
        seller_address=invoice_data.seller_address,
        seller_email=invoice_data.seller_email,
        buyer_name=invoice_data.buyer_name,
        buyer_address=invoice_data.buyer_address,
        buyer_email=invoice_data.buyer_email,
        # Kept for backward compatibility in existing UI pages.
        client_name=invoice_data.buyer_name,
        client_email=invoice_data.buyer_email,
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

    log_audit(db, "invoice", new_invoice.invoice_id, "create",
              changed_by=current_user.user_id if current_user else None)
    db.commit()
    db.refresh(new_invoice)
    return new_invoice


@router.get("/list", response_model=list[InvoiceResponse])
def list_invoices(
    # ---- Filters ----
    status: Optional[str] = Query(default=None, description="Comma-separated statuses, e.g. 'overdue,sent'"),
    search: Optional[str] = Query(default=None, description="Search buyer/seller name or invoice number"),
    date_from: Optional[date] = Query(default=None, description="Filter due_date >= date_from (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(default=None, description="Filter due_date <= date_to (YYYY-MM-DD)"),
    min_amount: Optional[float] = Query(default=None, description="Filter grand_total >= min_amount"),
    max_amount: Optional[float] = Query(default=None, description="Filter grand_total <= max_amount"),
    # ---- Sorting ----
    sort_by: str = Query(default="created_at", description="Field to sort by: created_at | due_date | grand_total | invoice_number | buyer_name"),
    sort_order: str = Query(default="desc", description="asc or desc"),
    # ---- Pagination ----
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    # Auto-mark overdue before returning
    changed = _auto_mark_overdue(db)
    if changed:
        db.commit()

    q = db.query(Invoice)

    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        q = q.filter(Invoice.status.in_(statuses))

    if search:
        term = f"%{search}%"
        q = q.filter(
            Invoice.buyer_name.ilike(term)
            | Invoice.seller_name.ilike(term)
            | Invoice.invoice_number.ilike(term)
        )

    if date_from:
        q = q.filter(Invoice.due_date >= date_from)
    if date_to:
        q = q.filter(Invoice.due_date <= date_to)
    if min_amount is not None:
        q = q.filter(Invoice.grand_total >= min_amount)
    if max_amount is not None:
        q = q.filter(Invoice.grand_total <= max_amount)

    sort_field_map = {
        "created_at": Invoice.created_at,
        "due_date": Invoice.due_date,
        "grand_total": Invoice.grand_total,
        "invoice_number": Invoice.invoice_number,
        "buyer_name": Invoice.buyer_name,
    }
    sort_col = sort_field_map.get(sort_by, Invoice.created_at)
    q = q.order_by(sort_col.asc() if sort_order == "asc" else sort_col.desc())

    offset = (page - 1) * page_size
    return q.offset(offset).limit(page_size).all()


# -------------------------------------------------------
# PUT /invoice/{invoice_id}/status – explicit status change
# -------------------------------------------------------
VALID_STATUSES = {"draft", "sent", "viewed", "paid", "overdue", "cancelled"}


@router.put("/{invoice_id}/status", response_model=InvoiceResponse)
def update_invoice_status(
    invoice_id: str,
    status: str = Query(description=f"New status. One of: {', '.join(sorted(VALID_STATUSES))}"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    old_status = invoice.status
    invoice.status = status
    log_audit(db, "invoice", invoice_id, "status_change",
              changed_by=current_user.user_id if current_user else None,
              changes={"status": {"old": old_status, "new": status}})
    db.commit()
    db.refresh(invoice)
    return invoice


# -------------------------------------------------------
# POST /invoice/check-overdue – manually trigger overdue detection
# -------------------------------------------------------
@router.post("/check-overdue", status_code=200)
def check_overdue(db: Session = Depends(get_db)):
    count = _auto_mark_overdue(db)
    db.commit()
    return {"marked_overdue": count}


# -------------------------------------------------------
# GET /invoice/import/{token} – claim invoice from email link
# -------------------------------------------------------
@router.get("/import/{token}", response_model=InvoiceResponse)
def import_invoice_from_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Called when the recipient clicks 'Add to My Invoice Library' in the email.
    Creates a copy of the original invoice owned by the current user (if logged
    in) and marks the one-time token as used.
    """
    import_token = (
        db.query(InvoiceImportToken)
        .filter(InvoiceImportToken.token == token)
        .first()
    )
    if not import_token:
        raise HTTPException(status_code=404, detail="Import link not found")
    if import_token.used_at is not None:
        raise HTTPException(status_code=410, detail="This import link has already been used")
    if datetime.now(timezone.utc) > import_token.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=410, detail="This import link has expired")

    original = db.query(Invoice).filter(Invoice.invoice_id == import_token.invoice_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Original invoice no longer exists")

    original_items = db.query(LineItem).filter(LineItem.invoice_id == original.invoice_id).all()

    # Mark invoice as "viewed" on the original (so the sender knows the link was clicked)
    if original.status == "sent":
        original.status = "viewed"

    # Create a copy for the recipient
    new_number = f"IMP-{str(uuid.uuid4())[:8].upper()}"
    imported = Invoice(
        invoice_number=new_number,
        owner_id=current_user.user_id if current_user else None,
        seller_name=original.seller_name,
        seller_address=original.seller_address,
        seller_email=original.seller_email,
        buyer_name=original.buyer_name,
        buyer_address=original.buyer_address,
        buyer_email=original.buyer_email,
        client_name=original.client_name,
        client_email=original.client_email,
        currency=original.currency,
        due_date=original.due_date,
        notes=original.notes,
        subtotal=original.subtotal,
        tax_total=original.tax_total,
        grand_total=original.grand_total,
        status="draft",
    )
    db.add(imported)
    db.flush()

    for item in original_items:
        db.add(LineItem(
            invoice_id=imported.invoice_id,
            item_number=item.item_number,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate,
            line_total=item.line_total,
        ))

    import_token.used_at = datetime.now(timezone.utc)
    import_token.imported_by = current_user.user_id if current_user else None

    log_audit(db, "invoice", imported.invoice_id, "imported",
              changed_by=current_user.user_id if current_user else None,
              changes={"source_invoice_id": original.invoice_id})
    db.commit()
    db.refresh(imported)
    return imported


@router.get("/fetch/{invoice_id}")
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
        if format != "json":
            raise HTTPException(status_code=400, detail="Unsupported format. Use one of: json, ubl, xml, csv, pdf")
        return InvoiceResponse.model_validate(invoice)


@router.put("/update/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: str,
    updates: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    update_data = updates.model_dump(exclude_unset=True)
    old_values = {k: str(getattr(invoice, k)) for k in update_data}
    for field, value in update_data.items():
        setattr(invoice, field, value)

    # Keep legacy client_* fields aligned with buyer_* values.
    if "buyer_name" in update_data:
        invoice.client_name = invoice.buyer_name
    if "buyer_email" in update_data:
        invoice.client_email = invoice.buyer_email
    if "client_name" in update_data:
        invoice.buyer_name = invoice.client_name
    if "client_email" in update_data:
        invoice.buyer_email = invoice.client_email

    log_audit(db, "invoice", invoice_id, "update",
              changed_by=current_user.user_id if current_user else None,
              changes={k: {"old": old_values[k], "new": str(update_data[k])} for k in update_data})
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/delete/{invoice_id}", status_code=200)
def delete_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    log_audit(db, "invoice", invoice_id, "delete",
              changed_by=current_user.user_id if current_user else None)
    db.delete(invoice)
    db.commit()
    return {"message": f"Invoice {invoice_id} deleted successfully"}


# Legacy Sprint 1 routes kept accessible in parallel
@legacy_router.post("/", response_model=InvoiceResponse, status_code=201)
def legacy_create_invoice(invoice_data: InvoiceCreate, db: Session = Depends(get_db)):
    return create_invoice(invoice_data, db)


@legacy_router.get("/", response_model=list[InvoiceResponse])
def legacy_list_invoices(db: Session = Depends(get_db)):
    return list_invoices(db)


@legacy_router.get("/{invoice_id}")
def legacy_get_invoice(
    invoice_id: str,
    format: str = Query(
        default="json",
        description="Output format: json, ubl, xml, csv, pdf"
    ),
    db: Session = Depends(get_db)
):
    return get_invoice(invoice_id, format, db)


@legacy_router.put("/{invoice_id}", response_model=InvoiceResponse)
def legacy_update_invoice(invoice_id: str, updates: InvoiceUpdate, db: Session = Depends(get_db)):
    return update_invoice(invoice_id, updates, db)


@legacy_router.delete("/{invoice_id}", status_code=200)
def legacy_delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    return delete_invoice(invoice_id, db)
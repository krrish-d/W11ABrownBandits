from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.invoice import Invoice, LineItem
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceUpdate
import uuid
from datetime import date
from lxml import etree

router = APIRouter(
    prefix="/invoices",
    tags=["Invoice Creation"]
)

# HELPER: Generate UBL 2.1 XML from an invoice object
def generate_ubl_xml(invoice: Invoice, items: list) -> str:
    # Define namespaces
    nsmap = {
        None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    }
    cac = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

    # Root element
    root = etree.Element("Invoice", nsmap=nsmap)

    # Basic fields
    etree.SubElement(root, f"{{{cbc}}}UBLVersionID").text = "2.1"
    etree.SubElement(root, f"{{{cbc}}}ID").text = invoice.invoice_number
    etree.SubElement(root, f"{{{cbc}}}IssueDate").text = str(invoice.due_date)
    etree.SubElement(root, f"{{{cbc}}}InvoiceTypeCode").text = "380"
    etree.SubElement(root, f"{{{cbc}}}DocumentCurrencyCode").text = invoice.currency

    # Supplier (seller) party
    supplier = etree.SubElement(root, f"{{{cac}}}AccountingSupplierParty")
    supplier_party = etree.SubElement(supplier, f"{{{cac}}}Party")
    supplier_name_el = etree.SubElement(supplier_party, f"{{{cac}}}PartyName")
    etree.SubElement(supplier_name_el, f"{{{cbc}}}Name").text = "Supplier"

    # Customer (buyer) party
    customer = etree.SubElement(root, f"{{{cac}}}AccountingCustomerParty")
    customer_party = etree.SubElement(customer, f"{{{cac}}}Party")
    customer_name_el = etree.SubElement(customer_party, f"{{{cac}}}PartyName")
    etree.SubElement(customer_name_el, f"{{{cbc}}}Name").text = invoice.client_name

    # Totals
    monetary_total = etree.SubElement(root, f"{{{cac}}}LegalMonetaryTotal")
    etree.SubElement(monetary_total, f"{{{cbc}}}LineExtensionAmount", currencyID=invoice.currency).text = str(invoice.subtotal)
    etree.SubElement(monetary_total, f"{{{cbc}}}TaxInclusiveAmount", currencyID=invoice.currency).text = str(invoice.grand_total)
    etree.SubElement(monetary_total, f"{{{cbc}}}PayableAmount", currencyID=invoice.currency).text = str(invoice.grand_total)

    # Line items
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


# POST /invoices — Create a new invoice
@router.post("/", response_model=InvoiceResponse, status_code=201)
def create_invoice(invoice_data: InvoiceCreate, db: Session = Depends(get_db)):
    # Generate invoice number
    invoice_number = f"INV-{str(uuid.uuid4())[:8].upper()}"

    # Calculate totals
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

    # Save invoice to database
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

    # Save line items
    saved_items = []
    for item_data in line_items_data:
        line_item = LineItem(
            invoice_id=new_invoice.invoice_id,
            **item_data
        )
        db.add(line_item)
        saved_items.append(line_item)

    db.commit()
    db.refresh(new_invoice)

    return new_invoice


# GET /invoices — List all invoices
@router.get("/", response_model=list[InvoiceResponse])
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()
    return invoices


# GET /invoices/{invoice_id} — Get a specific invoice
@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


# GET /invoices/{invoice_id}/xml — Get invoice as UBL XML
@router.get("/{invoice_id}/xml")
def get_invoice_xml(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    items = db.query(LineItem).filter(LineItem.invoice_id == invoice_id).all()
    xml_content = generate_ubl_xml(invoice, items)

    from fastapi.responses import Response
    return Response(content=xml_content, media_type="application/xml")


# PUT /invoices/{invoice_id} — Update an invoice
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


# DELETE /invoices/{invoice_id} — Delete an invoice
@router.delete("/{invoice_id}", status_code=200)
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    db.delete(invoice)
    db.commit()
    return {"message": f"Invoice {invoice_id} deleted successfully"}
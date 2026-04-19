import base64
import os
from datetime import datetime, timezone
from lxml import etree
import resend


CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"


# -------------------------------------------------------
# HELPER: Extract invoice ID from UBL XML
# -------------------------------------------------------
def extract_invoice_id(invoice_xml: str) -> str:
    try:
        root = etree.fromstring(invoice_xml.encode())
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML: {e}")

    invoice_id_el = root.find(f"{{{CBC}}}ID")
    if invoice_id_el is None or not invoice_id_el.text:
        raise ValueError("Invoice ID is missing in UBL XML")

    return invoice_id_el.text.strip()


# -------------------------------------------------------
# MAIN: Send invoice XML via Resend
# -------------------------------------------------------
def send_invoice_email(invoice_xml: str, recipient_email: str) -> dict:
    invoice_id = extract_invoice_id(invoice_xml)

    resend_api_key = os.getenv("RESEND_API_KEY")
    sender_email = os.getenv("COMMUNICATION_FROM_EMAIL")
    sender_name = os.getenv("COMMUNICATION_SENDER_NAME", "E-Invoice API")

    if not resend_api_key or not sender_email:
        raise ValueError("Missing Resend credentials. Set RESEND_API_KEY and COMMUNICATION_FROM_EMAIL")

    try:
        resend.api_key = resend_api_key
        resend.Emails.send({
            "from": f"{sender_name} <{sender_email}>",
            "to": [recipient_email],
            "subject": f"Invoice {invoice_id}",
            "text": "Please find the attached UBL XML invoice.",
            "attachments": [
                {
                    "filename": f"{invoice_id}.xml",
                    "content": base64.b64encode(invoice_xml.encode("utf-8")).decode("utf-8"),
                }
            ],
        })
    except Exception as e:
        raise RuntimeError(f"Failed to send invoice email: {e}")

    sent_at = datetime.now(timezone.utc)
    return {
        "status": "sent",
        "timestamp": sent_at,
        "recipient_email": recipient_email,
        "invoice_id": invoice_id
    }

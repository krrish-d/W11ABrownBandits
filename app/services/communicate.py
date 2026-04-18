import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from lxml import etree


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
# MAIN: Send invoice XML via Gmail SMTP
# -------------------------------------------------------
def send_invoice_email(invoice_xml: str, recipient_email: str) -> dict:
    invoice_id = extract_invoice_id(invoice_xml)

    smtp_host = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("GMAIL_SMTP_PORT", "587"))
    gmail_username = os.getenv("GMAIL_USERNAME")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
    sender_name = os.getenv("COMMUNICATION_SENDER_NAME", "E-Invoice API")

    if not gmail_username or not gmail_app_password:
        raise ValueError("Missing Gmail SMTP credentials. Set GMAIL_USERNAME and GMAIL_APP_PASSWORD")

    message = EmailMessage()
    message["Subject"] = f"Invoice {invoice_id}"
    message["From"] = f"{sender_name} <{gmail_username}>"
    message["To"] = recipient_email
    message.set_content("Please find the attached UBL XML invoice.")
    message.add_attachment(
        invoice_xml.encode("utf-8"),
        maintype="application",
        subtype="xml",
        filename=f"{invoice_id}.xml"
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(gmail_username, gmail_app_password)
            smtp.send_message(message)
    except smtplib.SMTPException as e:
        raise RuntimeError(f"Failed to send invoice email: {e}")

    sent_at = datetime.now(timezone.utc)
    return {
        "status": "sent",
        "timestamp": sent_at,
        "recipient_email": recipient_email,
        "invoice_id": invoice_id
    }

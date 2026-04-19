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


def _resend_credentials() -> tuple[str, str, str]:
    """Return (api_key, sender_email, sender_name) or raise ValueError."""
    api_key = os.getenv("RESEND_API_KEY")
    sender_email = os.getenv("COMMUNICATION_FROM_EMAIL")
    sender_name = os.getenv("COMMUNICATION_SENDER_NAME", "E-Invoice API")
    if not api_key or not sender_email:
        raise ValueError("Missing Resend credentials. Set RESEND_API_KEY and COMMUNICATION_FROM_EMAIL")
    return api_key, sender_email, sender_name


# -------------------------------------------------------
# ORIGINAL: Send invoice XML via Resend (kept for backward compat)
# -------------------------------------------------------
def send_invoice_email(invoice_xml: str, recipient_email: str) -> dict:
    invoice_id = extract_invoice_id(invoice_xml)

    resend_api_key, sender_email, sender_name = _resend_credentials()

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


# -------------------------------------------------------
# NEW: Send rich HTML invoice email with "Add to Library" button
# -------------------------------------------------------
def send_invoice_with_import_link(
    invoice,        # app.models.invoice.Invoice ORM instance
    items: list,    # list of LineItem ORM instances
    recipient_email: str,
    import_token: str,
) -> dict:
    """
    Sends a styled HTML email to *recipient_email* that includes a prominent
    'Add to My Invoice Library' button.  Clicking the button hits the backend
    import endpoint which creates a copy of the invoice in the recipient's
    account.
    """
    resend_api_key, sender_email, sender_name = _resend_credentials()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    import_url = f"{frontend_url}/invoice/import/{import_token}"

    # Build the line-items HTML table rows
    item_rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{it.description}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:center'>{it.quantity}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right'>"
        f"{invoice.currency} {it.unit_price:.2f}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right'>"
        f"{invoice.currency} {it.line_total:.2f}</td>"
        f"</tr>"
        for it in items
    )

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Invoice {invoice.invoice_number}</title></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background:#f3f4f6;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr><td style="background:#2563eb;padding:28px 32px;">
          <h1 style="margin:0;color:#ffffff;font-size:22px;">Invoice {invoice.invoice_number}</h1>
          <p style="margin:4px 0 0;color:#bfdbfe;font-size:14px;">from {invoice.seller_name}</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr>
              <td style="width:50%;vertical-align:top;">
                <p style="margin:0 0 4px;font-size:12px;color:#6b7280;text-transform:uppercase;">From</p>
                <p style="margin:0;font-weight:bold;color:#111827">{invoice.seller_name}</p>
                <p style="margin:0;font-size:14px;color:#374151">{invoice.seller_address}</p>
                <p style="margin:0;font-size:14px;color:#374151">{invoice.seller_email}</p>
              </td>
              <td style="width:50%;vertical-align:top;text-align:right;">
                <p style="margin:0 0 4px;font-size:12px;color:#6b7280;text-transform:uppercase;">Bill To</p>
                <p style="margin:0;font-weight:bold;color:#111827">{invoice.buyer_name}</p>
                <p style="margin:0;font-size:14px;color:#374151">{invoice.buyer_address}</p>
                <p style="margin:0;font-size:14px;color:#374151">{invoice.buyer_email}</p>
              </td>
            </tr>
          </table>

          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr>
              <td style="padding:12px 16px;background:#eff6ff;border-radius:6px;width:33%;">
                <p style="margin:0;font-size:11px;color:#6b7280;text-transform:uppercase;">Invoice #</p>
                <p style="margin:4px 0 0;font-weight:bold;color:#1d4ed8">{invoice.invoice_number}</p>
              </td>
              <td style="width:8px;"></td>
              <td style="padding:12px 16px;background:#eff6ff;border-radius:6px;width:33%;">
                <p style="margin:0;font-size:11px;color:#6b7280;text-transform:uppercase;">Due Date</p>
                <p style="margin:4px 0 0;font-weight:bold;color:#1d4ed8">{invoice.due_date}</p>
              </td>
              <td style="width:8px;"></td>
              <td style="padding:12px 16px;background:#eff6ff;border-radius:6px;width:33%;text-align:right;">
                <p style="margin:0;font-size:11px;color:#6b7280;text-transform:uppercase;">Amount Due</p>
                <p style="margin:4px 0 0;font-weight:bold;color:#1d4ed8;font-size:18px;">
                  {invoice.currency} {invoice.grand_total:.2f}</p>
              </td>
            </tr>
          </table>

          <!-- Line items -->
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;margin-bottom:24px;">
            <thead>
              <tr style="background:#f9fafb;">
                <th style="padding:10px 8px;text-align:left;font-size:12px;color:#6b7280;font-weight:600">Description</th>
                <th style="padding:10px 8px;text-align:center;font-size:12px;color:#6b7280;font-weight:600">Qty</th>
                <th style="padding:10px 8px;text-align:right;font-size:12px;color:#6b7280;font-weight:600">Unit Price</th>
                <th style="padding:10px 8px;text-align:right;font-size:12px;color:#6b7280;font-weight:600">Total</th>
              </tr>
            </thead>
            <tbody>{item_rows}</tbody>
            <tfoot>
              <tr><td colspan="3" style="padding:8px;text-align:right;font-size:13px;color:#6b7280">Subtotal</td>
                  <td style="padding:8px;text-align:right;font-size:13px">{invoice.currency} {invoice.subtotal:.2f}</td></tr>
              <tr><td colspan="3" style="padding:8px;text-align:right;font-size:13px;color:#6b7280">Tax</td>
                  <td style="padding:8px;text-align:right;font-size:13px">{invoice.currency} {invoice.tax_total:.2f}</td></tr>
              <tr style="background:#f9fafb;">
                <td colspan="3" style="padding:10px 8px;text-align:right;font-weight:bold">Grand Total</td>
                <td style="padding:10px 8px;text-align:right;font-weight:bold;color:#2563eb">
                  {invoice.currency} {invoice.grand_total:.2f}</td>
              </tr>
            </tfoot>
          </table>

          <!-- CTA button -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
            <tr><td align="center">
              <a href="{import_url}"
                 style="display:inline-block;padding:14px 32px;background:#2563eb;color:#ffffff;
                        font-size:15px;font-weight:bold;text-decoration:none;border-radius:6px;">
                &#x2B; Add to My Invoice Library
              </a>
            </td></tr>
          </table>
          <p style="text-align:center;font-size:12px;color:#9ca3af;margin:0">
            Or copy this link: <a href="{import_url}" style="color:#2563eb">{import_url}</a>
          </p>
          <p style="text-align:center;font-size:11px;color:#d1d5db;margin:12px 0 0">
            This link expires in 7 days and can only be used once.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb;">
          <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center">
            Sent by {sender_name} · Powered by E-Invoice API
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    try:
        resend.api_key = resend_api_key
        resend.Emails.send({
            "from": f"{sender_name} <{sender_email}>",
            "to": [recipient_email],
            "subject": f"Invoice {invoice.invoice_number} from {invoice.seller_name} – {invoice.currency} {invoice.grand_total:.2f} due {invoice.due_date}",
            "html": html,
        })
    except Exception as e:
        raise RuntimeError(f"Failed to send invoice email: {e}")

    return {
        "status": "sent",
        "timestamp": datetime.now(timezone.utc),
        "recipient_email": recipient_email,
        "invoice_id": invoice.invoice_id,
        "import_url": import_url,
    }


# -------------------------------------------------------
# NEW: Send payment reminder for an overdue invoice
# -------------------------------------------------------
def send_payment_reminder(invoice) -> None:
    """
    Sends a short plain-text reminder email to the buyer for an overdue invoice.
    Raises RuntimeError on delivery failure.
    """
    resend_api_key, sender_email, sender_name = _resend_credentials()

    from datetime import date
    days_overdue = (date.today() - invoice.due_date).days

    html = f"""
<html><body style="font-family:Arial,sans-serif;color:#374151">
  <h2 style="color:#dc2626">Payment Reminder – Invoice {invoice.invoice_number}</h2>
  <p>Dear {invoice.buyer_name},</p>
  <p>This is a friendly reminder that the following invoice is now
     <strong style="color:#dc2626">{days_overdue} day{'s' if days_overdue != 1 else ''} overdue</strong>:</p>
  <table style="border-collapse:collapse;margin:16px 0">
    <tr><td style="padding:4px 12px 4px 0;color:#6b7280">Invoice #</td>
        <td style="padding:4px 0"><strong>{invoice.invoice_number}</strong></td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#6b7280">Due Date</td>
        <td style="padding:4px 0">{invoice.due_date}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#6b7280">Amount Due</td>
        <td style="padding:4px 0"><strong>{invoice.currency} {invoice.grand_total:.2f}</strong></td></tr>
  </table>
  <p>Please arrange payment at your earliest convenience.  If you have already
     paid, please disregard this message.</p>
  <p>Regards,<br>{invoice.seller_name}</p>
</body></html>
"""

    try:
        resend.api_key = resend_api_key
        resend.Emails.send({
            "from": f"{sender_name} <{sender_email}>",
            "to": [invoice.buyer_email],
            "subject": f"Payment Reminder – Invoice {invoice.invoice_number} is {days_overdue} days overdue",
            "html": html,
        })
    except Exception as e:
        raise RuntimeError(f"Failed to send reminder email: {e}")

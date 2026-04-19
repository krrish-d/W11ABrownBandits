"""
Background scheduler – runs three recurring jobs:

  1. check_overdue_invoices   – every 6 hours
  2. generate_recurring       – daily at 08:00 local time
  3. send_overdue_reminders   – daily at 09:00 local time

Each job creates its own DB session so it is safe to run in a background
thread alongside the FastAPI worker thread.

NOTE: When running with multiple Uvicorn workers (--workers N > 1) each
process starts its own scheduler, which can cause duplicate invoice
generation.  For production, pin workers=1 or use a distributed lock /
external job queue.
"""

import calendar
import json
import logging
import os
import uuid
from datetime import date, timedelta, datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def _get_db():
    from app.database import SessionLocal
    return SessionLocal()


def get_next_run_date(current: date, frequency: str) -> date:
    if frequency == "daily":
        return current + timedelta(days=1)
    if frequency == "weekly":
        return current + timedelta(weeks=1)
    if frequency == "biweekly":
        return current + timedelta(weeks=2)
    if frequency == "monthly":
        month = current.month + 1
        year = current.year
        if month > 12:
            month = 1
            year += 1
        day = min(current.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if frequency == "quarterly":
        month = current.month + 3
        year = current.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(current.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if frequency == "annually":
        try:
            return current.replace(year=current.year + 1)
        except ValueError:
            return current.replace(year=current.year + 1, day=28)
    raise ValueError(f"Unknown frequency: {frequency}")


# -------------------------------------------------------
# Job 1 – mark overdue invoices
# -------------------------------------------------------

def check_overdue_invoices():
    from app.models.invoice import Invoice
    from app.services.audit import log_audit

    db = _get_db()
    try:
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
        db.commit()
        if candidates:
            logger.info("Marked %d invoices as overdue", len(candidates))
    except Exception:
        logger.exception("check_overdue_invoices failed")
        db.rollback()
    finally:
        db.close()


# -------------------------------------------------------
# Job 2 – generate recurring invoices
# -------------------------------------------------------

def generate_recurring_invoices():
    from app.models.invoice import Invoice, LineItem
    from app.models.recurring import RecurringInvoice
    from app.services.audit import log_audit

    db = _get_db()
    try:
        today = date.today()
        rules = (
            db.query(RecurringInvoice)
            .filter(
                RecurringInvoice.is_active == True,
                RecurringInvoice.next_run_date <= today,
            )
            .all()
        )
        created = 0
        for rule in rules:
            if rule.end_date and today > rule.end_date:
                rule.is_active = False
                continue

            try:
                tmpl = json.loads(rule.invoice_template)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Recurring rule %s has invalid template JSON", rule.recurring_id)
                continue

            invoice_number = f"INV-{str(uuid.uuid4())[:8].upper()}"
            subtotal = 0.0
            tax_total = 0.0
            line_items_data = []

            for item in tmpl.get("items", []):
                line_total = round(item["quantity"] * item["unit_price"], 2)
                tax_amount = round(line_total * (item.get("tax_rate", 0) / 100), 2)
                subtotal += line_total
                tax_total += tax_amount
                line_items_data.append({
                    "item_number": item.get("item_number", "1"),
                    "description": item["description"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "tax_rate": item.get("tax_rate", 0),
                    "line_total": line_total,
                })

            subtotal = round(subtotal, 2)
            tax_total = round(tax_total, 2)
            grand_total = round(subtotal + tax_total, 2)

            # Parse due_date: use today + payment_terms days if not specified
            raw_due = tmpl.get("due_date")
            if raw_due:
                try:
                    due_date = date.fromisoformat(raw_due)
                except ValueError:
                    due_date = today + timedelta(days=30)
            else:
                due_date = today + timedelta(days=30)

            new_inv = Invoice(
                invoice_number=invoice_number,
                owner_id=rule.owner_id,
                seller_name=tmpl.get("seller_name", ""),
                seller_address=tmpl.get("seller_address", ""),
                seller_email=tmpl.get("seller_email", ""),
                buyer_name=tmpl.get("buyer_name", ""),
                buyer_address=tmpl.get("buyer_address", ""),
                buyer_email=tmpl.get("buyer_email", ""),
                client_name=tmpl.get("buyer_name", ""),
                client_email=tmpl.get("buyer_email", ""),
                currency=tmpl.get("currency", "AUD"),
                due_date=due_date,
                notes=tmpl.get("notes"),
                subtotal=subtotal,
                tax_total=tax_total,
                grand_total=grand_total,
            )
            db.add(new_inv)
            db.flush()

            for item_data in line_items_data:
                db.add(LineItem(invoice_id=new_inv.invoice_id, **item_data))

            log_audit(db, "invoice", new_inv.invoice_id, "create",
                      changed_by="system",
                      changes={"source": "recurring", "recurring_id": rule.recurring_id})

            rule.last_run_date = today
            rule.next_run_date = get_next_run_date(today, rule.frequency)
            created += 1

        db.commit()
        if created:
            logger.info("Generated %d recurring invoices", created)
    except Exception:
        logger.exception("generate_recurring_invoices failed")
        db.rollback()
    finally:
        db.close()


# -------------------------------------------------------
# Job 3 – send overdue reminders
# -------------------------------------------------------

def send_overdue_reminders():
    """
    Sends a reminder email for every overdue invoice that has a known
    buyer_email.  Skips invoices that already received a reminder today
    (checked via communication_logs).
    """
    from app.models.invoice import Invoice
    from app.models.communication import CommunicationLog
    from app.services.communicate import send_payment_reminder

    resend_api_key = os.getenv("RESEND_API_KEY")
    sender_email = os.getenv("COMMUNICATION_FROM_EMAIL")
    if not resend_api_key or not sender_email:
        return  # silently skip if Resend is not configured

    db = _get_db()
    try:
        today = date.today()
        overdue_invoices = (
            db.query(Invoice)
            .filter(Invoice.status == "overdue", Invoice.buyer_email != "")
            .all()
        )
        sent = 0
        for inv in overdue_invoices:
            # Check if a reminder was already sent today
            already_sent = (
                db.query(CommunicationLog)
                .filter(
                    CommunicationLog.invoice_id == inv.invoice_id,
                    CommunicationLog.delivery_status == "reminder",
                )
                .first()
            )
            if already_sent:
                continue
            try:
                send_payment_reminder(inv)
                log = CommunicationLog(
                    invoice_id=inv.invoice_id,
                    recipient_email=inv.buyer_email,
                    delivery_status="reminder",
                )
                db.add(log)
                sent += 1
            except Exception:
                logger.exception("Failed to send reminder for invoice %s", inv.invoice_id)

        db.commit()
        if sent:
            logger.info("Sent %d overdue reminders", sent)
    except Exception:
        logger.exception("send_overdue_reminders failed")
        db.rollback()
    finally:
        db.close()


# -------------------------------------------------------
# Scheduler lifecycle
# -------------------------------------------------------

def start_scheduler():
    scheduler.add_job(
        check_overdue_invoices,
        IntervalTrigger(hours=6),
        id="check_overdue",
        replace_existing=True,
    )
    scheduler.add_job(
        generate_recurring_invoices,
        CronTrigger(hour=8, minute=0),
        id="recurring_invoices",
        replace_existing=True,
    )
    scheduler.add_job(
        send_overdue_reminders,
        CronTrigger(hour=9, minute=0),
        id="overdue_reminders",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")

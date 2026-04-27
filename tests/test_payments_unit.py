"""Unit tests for app.routers.payments helper logic."""

from unittest.mock import MagicMock

from app.routers.payments import _refresh_invoice_status


def _fake_db_with_total(total: float):
    """Build a MagicMock that returns ``total`` from the payment-sum query."""
    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = total
    return db


def test_refresh_marks_paid_when_payments_meet_total():
    invoice = MagicMock()
    invoice.invoice_id = "inv-1"
    invoice.grand_total = 100.0
    invoice.status = "sent"

    _refresh_invoice_status(invoice, _fake_db_with_total(100.0))
    assert invoice.status == "paid"


def test_refresh_marks_paid_when_payments_exceed_total():
    invoice = MagicMock()
    invoice.invoice_id = "inv-1"
    invoice.grand_total = 100.0
    invoice.status = "sent"

    _refresh_invoice_status(invoice, _fake_db_with_total(150.0))
    assert invoice.status == "paid"


def test_refresh_does_not_change_status_when_partial():
    invoice = MagicMock()
    invoice.invoice_id = "inv-1"
    invoice.grand_total = 100.0
    invoice.status = "sent"

    _refresh_invoice_status(invoice, _fake_db_with_total(50.0))
    assert invoice.status == "sent"


def test_refresh_does_not_overwrite_cancelled():
    invoice = MagicMock()
    invoice.invoice_id = "inv-1"
    invoice.grand_total = 100.0
    invoice.status = "cancelled"

    _refresh_invoice_status(invoice, _fake_db_with_total(100.0))
    assert invoice.status == "cancelled"


def test_refresh_handles_zero_payment_total():
    invoice = MagicMock()
    invoice.invoice_id = "inv-1"
    invoice.grand_total = 100.0
    invoice.status = "draft"

    _refresh_invoice_status(invoice, _fake_db_with_total(0.0))
    assert invoice.status == "draft"


def test_refresh_handles_none_payment_total():
    """When no payments exist the SUM query returns None; helper must still cope."""
    invoice = MagicMock()
    invoice.invoice_id = "inv-1"
    invoice.grand_total = 100.0
    invoice.status = "draft"

    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = None

    _refresh_invoice_status(invoice, db)
    assert invoice.status == "draft"

"""
Webhook receivers for third-party integrations (stubs for extension).

Xero / QuickBooks
-----------------
  POST /webhooks/xero        – receives Xero webhook events (stub, extend as needed)
  POST /webhooks/quickbooks  – receives QuickBooks webhook events (stub)
"""

import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# -------------------------------------------------------
# Xero (stub – extend with actual Xero webhook logic)
# -------------------------------------------------------

@router.post("/xero", status_code=200)
async def xero_webhook(request: Request):
    """
    Stub receiver for Xero webhooks.
    Xero sends events when invoices are paid or updated in Xero.

    To implement fully:
    1. Verify the 'x-xero-signature' header using your Xero webhook key.
    2. Parse the payload and match on InvoiceNumber or ExternalLinkId.
    3. Update the local invoice status accordingly.
    """
    payload = await request.json()
    logger.info("Received Xero webhook: %s", payload)
    return {"received": True}


# -------------------------------------------------------
# QuickBooks (stub)
# -------------------------------------------------------

@router.post("/quickbooks", status_code=200)
async def quickbooks_webhook(request: Request):
    """
    Stub receiver for QuickBooks Online webhooks.

    To implement fully:
    1. Verify the 'intuit-signature' header using your QuickBooks verifier token.
    2. Parse the EventNotification array and handle Invoice entity changes.
    3. Sync status (paid, voided, etc.) to the local invoice.
    """
    payload = await request.json()
    logger.info("Received QuickBooks webhook: %s", payload)
    return {"received": True}

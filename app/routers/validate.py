from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.validate import validate

router = APIRouter(tags=["Invoice Validation"])


class ValidationRequest(BaseModel):
    invoice_xml: str
    ruleset: str = "ubl"


class BulkValidationRequest(BaseModel):
    invoices: list[str]
    ruleset: str = "ubl"


@router.post("/validate")
def validate_invoice(request: ValidationRequest):
    """
    Validate a UBL 2.1 XML invoice (well-formedness, required fields, business rules, ruleset extras).

    Supported rulesets: ubl (default), peppol, australian
    """
    try:
        result = validate(request.invoice_xml, request.ruleset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return result


@router.get("/validate/rulesets")
def get_supported_rulesets():
    return {
        "rulesets": ["ubl", "peppol", "australian"],
        "default": "ubl",
        "descriptions": {
            "ubl": "Base UBL 2.1 schema validation",
            "peppol": "PEPPOL rules including TaxTotal and Party identification",
            "australian": "Australian-specific rules including AUD currency and ABN",
        },
    }


@router.post("/validate/bulk")
def validate_bulk(request: BulkValidationRequest):
    """
    Validate multiple UBL 2.1 XML invoices in a single request.

    Supported rulesets: ubl (default), peppol, australian
    """
    try:
        results = [
            {"index": i, **validate(xml, request.ruleset)}
            for i, xml in enumerate(request.invoices)
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {"results": results}

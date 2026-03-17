from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.validate import validate

router = APIRouter(
    prefix="/validate",
    tags=["Invoice Validation"]
)


class ValidationRequest(BaseModel):
    invoice_xml: str
    ruleset: str = "ubl"


# -------------------------------------------------------
# POST /validate — Validate a UBL XML invoice
# -------------------------------------------------------
@router.post("/")
def validate_invoice(request: ValidationRequest):
    """
    Validate a UBL 2.1 XML invoice.

    Supported rulesets:
    - ubl        (default): Base UBL 2.1 schema validation
    - peppol:    PEPPOL rules on top of UBL
    - australian: Australian-specific rules on top of UBL

    Returns a validation report with:
    - overall result (valid: true/false)
    - list of errors with severity (Critical or Warning)
    - the specific rule each error relates to
    """
    try:
        result = validate(request.invoice_xml, request.ruleset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


# -------------------------------------------------------
# GET /validate/rulesets — List supported rulesets
# -------------------------------------------------------
@router.get("/rulesets")
def get_supported_rulesets():
    """
    Returns the list of supported validation rulesets.
    """
    return {
        "rulesets": ["ubl", "peppol", "australian"],
        "default": "ubl",
        "descriptions": {
            "ubl": "Base UBL 2.1 schema validation",
            "peppol": "PEPPOL rules including TaxTotal and Party identification",
            "australian": "Australian-specific rules including AUD currency and ABN"
        }
    }
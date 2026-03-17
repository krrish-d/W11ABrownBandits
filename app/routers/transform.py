import base64
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from app.services.transform import transform

router = APIRouter(
    prefix="/transform",
    tags=["Invoice Transformation"]
)


class TransformRequest(BaseModel):
    input_format: str
    output_format: str
    invoice_data: Optional[str] = None
    invoice_data_base64: Optional[str] = None


@router.post("/")
def transform_invoice(request: TransformRequest):
    """
    Transform an invoice into UBL 2.1 XML.

    Supported input formats: json, csv, xml, ubl_xml, pdf
    Output format: ubl_xml only

    For PDF input, provide the PDF as a base64-encoded string in invoice_data_base64.
    For all other formats, provide the data as a string in invoice_data.
    """
    try:
        if request.input_format.lower().strip() == "pdf":
            if not request.invoice_data_base64:
                raise HTTPException(
                    status_code=400,
                    detail="PDF input must be provided as base64-encoded string in 'invoice_data_base64'"
                )
            try:
                pdf_bytes = base64.b64decode(request.invoice_data_base64)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid base64 encoding for PDF input"
                )
            result = transform(request.input_format, request.output_format, pdf_bytes)
        else:
            if not request.invoice_data:
                raise HTTPException(
                    status_code=400,
                    detail="invoice_data is required for non-PDF formats"
                )
            result = transform(request.input_format, request.output_format, request.invoice_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(content=result, media_type="application/xml")


@router.get("/formats")
def get_supported_formats():
    """
    Returns the list of supported input and output formats for invoice transformation.
    """
    return {
        "input_formats": ["json", "csv", "xml", "ubl_xml", "pdf"],
        "output_formats": ["ubl_xml"],
        "note": "PDF input must be provided as base64-encoded string in 'invoice_data_base64'"
    }
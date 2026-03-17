from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.transform import transform

router = APIRouter(
    prefix="/transform",
    tags=["Invoice Transformation"]
)


class TransformRequest(BaseModel):
    input_format: str
    output_format: str
    invoice_data: str


@router.post("/")
def transform_invoice(request: TransformRequest):
    """
    Transform an invoice between supported formats.

    Supported input formats:  json, csv, ubl_xml
    Supported output formats: json, csv, ubl_xml, pdf

    Supported conversions:
    - JSON     → UBL XML
    - JSON     → CSV
    - JSON     → PDF
    - CSV      → UBL XML
    - CSV      → JSON
    - CSV      → PDF
    - UBL XML  → JSON
    - UBL XML  → CSV
    - UBL XML  → PDF
    """
    try:
        result = transform(request.input_format, request.output_format, request.invoice_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if request.output_format == "ubl_xml":
        return Response(content=result, media_type="application/xml")
    elif request.output_format == "csv":
        return Response(
            content=result,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=invoice.csv"}
        )
    elif request.output_format == "pdf":
        return Response(
            content=result,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=invoice.pdf"}
        )
    else:
        return {"status": "success", "converted_invoice": result}

@router.get("/formats")
def get_supported_formats():
    """
    Returns the list of supported input and output formats for invoice transformation.
    """
    return {
        "input_formats": ["json", "csv", "ubl_xml"],
        "output_formats": ["json", "csv", "ubl_xml", "pdf"],
        "supported_conversions": [
            "json → ubl_xml",
            "json → csv",
            "json → pdf",
            "csv → ubl_xml",
            "csv → json",
            "csv → pdf",
            "ubl_xml → json",
            "ubl_xml → csv",
            "ubl_xml → pdf"
        ]
    }
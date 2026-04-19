import base64
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.transform import transform

router = APIRouter(tags=["Invoice Transformation"])


class TransformRequest(BaseModel):
    input_format: str
    output_format: str
    invoice_data: Optional[str] = None
    invoice_data_base64: Optional[str] = None
    xml_type: Optional[str] = "ubl"


@router.post("/transform")
def transform_invoice(request: TransformRequest):
    """
    Transform an invoice between supported formats.

    Supported input formats:  json, csv, xml, ubl_xml, pdf
    Supported output formats: json, csv, xml, ubl_xml, pdf

    For PDF input, provide the PDF as a base64-encoded string in invoice_data_base64.
    For all other formats, provide the data as a string in invoice_data.

    When output_format is 'xml', use xml_type to specify:
    - 'ubl' (default): outputs UBL 2.1 XML
    - 'generic': outputs simple generic XML
    """
    try:
        if request.input_format.lower().strip() == "pdf":
            if not request.invoice_data_base64:
                raise HTTPException(
                    status_code=400,
                    detail="PDF input must be provided as base64-encoded string in 'invoice_data_base64'",
                )
            try:
                pdf_bytes = base64.b64decode(request.invoice_data_base64)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid base64 encoding for PDF input",
                ) from None
            result = transform(
                request.input_format,
                request.output_format,
                pdf_bytes,
                request.xml_type or "ubl",
            )
        else:
            if not request.invoice_data:
                raise HTTPException(
                    status_code=400,
                    detail="invoice_data is required for non-PDF formats",
                )
            result = transform(
                request.input_format,
                request.output_format,
                request.invoice_data,
                request.xml_type or "ubl",
            )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if request.output_format == "ubl_xml" or request.output_format == "xml":
        return Response(content=result, media_type="application/xml")
    if request.output_format == "csv":
        return Response(
            content=result,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=invoice.csv"},
        )
    if request.output_format == "pdf":
        return Response(
            content=result,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=invoice.pdf"},
        )
    return {"status": "success", "converted_invoice": result}


@router.get("/transform/formats")
def get_supported_formats():
    return {
        "input_formats": ["json", "csv", "xml", "ubl_xml", "pdf"],
        "output_formats": ["json", "csv", "xml", "ubl_xml", "pdf"],
        "supported_conversions": [
            "json → ubl_xml",
            "json → csv",
            "json → pdf",
            "csv → ubl_xml",
            "csv → json",
            "csv → pdf",
            "ubl_xml → json",
            "ubl_xml → csv",
            "ubl_xml → pdf",
        ],
        "xml_type_options": ["ubl", "generic"],
        "note_pdf_input": "PDF input must be provided as base64-encoded string in 'invoice_data_base64'",
        "note_xml_output": "When output_format is 'xml', use xml_type to specify 'ubl' or 'generic' (default: 'ubl')",
    }

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.template import InvoiceTemplate
from app.models.user import User
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.services.audit import log_audit
from app.services.auth import get_optional_current_user, scope_query_to_owner, user_owns_record

router = APIRouter(prefix="/templates", tags=["Invoice Templates"])


# -------------------------------------------------------
# POST /templates
# -------------------------------------------------------
@router.post("", response_model=TemplateResponse, status_code=201)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    owner_id = current_user.user_id if current_user else None

    # If this template is set as default, unset any existing default for this owner
    if payload.is_default:
        existing_defaults = (
            db.query(InvoiceTemplate)
            .filter(InvoiceTemplate.owner_id == owner_id, InvoiceTemplate.is_default == True)  # noqa: E712
            .all()
        )
        for t in existing_defaults:
            t.is_default = False

    template = InvoiceTemplate(owner_id=owner_id, **payload.model_dump())
    db.add(template)
    # Flush so SQLAlchemy assigns template_id before we reference it in the audit log
    db.flush()
    log_audit(db, "template", template.template_id, "create",
              changed_by=owner_id)
    db.commit()
    db.refresh(template)
    return template


# -------------------------------------------------------
# GET /templates
# -------------------------------------------------------
@router.get("", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    q = scope_query_to_owner(
        db.query(InvoiceTemplate), InvoiceTemplate.owner_id, current_user
    )
    return q.order_by(InvoiceTemplate.is_default.desc(), InvoiceTemplate.name).all()


# -------------------------------------------------------
# GET /templates/{template_id}
# -------------------------------------------------------
@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    template = db.query(InvoiceTemplate).filter(InvoiceTemplate.template_id == template_id).first()
    if not template or not user_owns_record(current_user, template.owner_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return template


# -------------------------------------------------------
# PUT /templates/{template_id}
# -------------------------------------------------------
@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: str,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    template = db.query(InvoiceTemplate).filter(InvoiceTemplate.template_id == template_id).first()
    if not template or not user_owns_record(current_user, template.owner_id):
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = payload.model_dump(exclude_unset=True)

    if update_data.get("is_default"):
        owner_id = current_user.user_id if current_user else None
        existing_defaults = (
            db.query(InvoiceTemplate)
            .filter(
                InvoiceTemplate.owner_id == owner_id,
                InvoiceTemplate.is_default == True,  # noqa: E712
                InvoiceTemplate.template_id != template_id,
            )
            .all()
        )
        for t in existing_defaults:
            t.is_default = False

    for field, value in update_data.items():
        setattr(template, field, value)

    log_audit(db, "template", template_id, "update",
              changed_by=current_user.user_id if current_user else None)
    db.commit()
    db.refresh(template)
    return template


# -------------------------------------------------------
# DELETE /templates/{template_id}
# -------------------------------------------------------
@router.delete("/{template_id}", status_code=200)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    template = db.query(InvoiceTemplate).filter(InvoiceTemplate.template_id == template_id).first()
    if not template or not user_owns_record(current_user, template.owner_id):
        raise HTTPException(status_code=404, detail="Template not found")
    log_audit(db, "template", template_id, "delete",
              changed_by=current_user.user_id if current_user else None)
    db.delete(template)
    db.commit()
    return {"message": f"Template {template_id} deleted"}

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.user import User
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.services.auth import get_optional_current_user
from app.services.audit import log_audit

router = APIRouter(prefix="/clients", tags=["Client Management"])


# -------------------------------------------------------
# POST /clients
# -------------------------------------------------------
@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    client = Client(
        owner_id=current_user.user_id if current_user else None,
        **payload.model_dump(),
    )
    db.add(client)
    log_audit(db, "client", client.client_id, "create",
              changed_by=current_user.user_id if current_user else None)
    db.commit()
    db.refresh(client)
    return client


# -------------------------------------------------------
# GET /clients
# -------------------------------------------------------
@router.get("", response_model=list[ClientResponse])
def list_clients(
    search: Optional[str] = Query(default=None, description="Search by name or email"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    q = db.query(Client)
    if current_user:
        # Show the user's own clients plus unowned ones
        q = q.filter(
            (Client.owner_id == current_user.user_id) | (Client.owner_id == None)  # noqa: E711
        )
    if search:
        term = f"%{search}%"
        q = q.filter(Client.name.ilike(term) | Client.email.ilike(term))
    return q.order_by(Client.name).all()


# -------------------------------------------------------
# GET /clients/{client_id}
# -------------------------------------------------------
@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


# -------------------------------------------------------
# PUT /clients/{client_id}
# -------------------------------------------------------
@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: str,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = payload.model_dump(exclude_unset=True)
    old_values = {k: getattr(client, k) for k in update_data}
    for field, value in update_data.items():
        setattr(client, field, value)

    log_audit(db, "client", client_id, "update",
              changed_by=current_user.user_id if current_user else None,
              changes={k: {"old": str(old_values[k]), "new": str(update_data[k])} for k in update_data})
    db.commit()
    db.refresh(client)
    return client


# -------------------------------------------------------
# DELETE /clients/{client_id}
# -------------------------------------------------------
@router.delete("/{client_id}", status_code=200)
def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    log_audit(db, "client", client_id, "delete",
              changed_by=current_user.user_id if current_user else None)
    db.delete(client)
    db.commit()
    return {"message": f"Client {client_id} deleted successfully"}

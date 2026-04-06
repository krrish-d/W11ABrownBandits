from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Invoice Communication"])


@router.post("/communicate/send")
def communicate_send():
    """Deferred — route reserved for API contract."""
    raise HTTPException(status_code=501, detail="Email send is not implemented yet")


@router.get("/communicate/logs")
def communicate_logs():
    """Deferred — returns empty history until send is implemented."""
    return {"logs": []}

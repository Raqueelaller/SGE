from fastapi import APIRouter, Depends
from app.core.security import require_token

router = APIRouter(prefix="/private", tags=["private"])

@router.get("/whoami")
def whoami(user=Depends(require_token)):
    return {"ok": True, "message": "TOKEN OK", "data": user}

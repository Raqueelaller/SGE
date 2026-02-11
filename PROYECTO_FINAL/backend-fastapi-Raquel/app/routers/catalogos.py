from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.security import require_token

router = APIRouter(prefix="/catalogos", tags=["catalogos"])

@router.get("/provincias")
def get_provincias(
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    rows = db.execute(text("""
        SELECT id_provincia, provincia
        FROM sgi_provincias
        ORDER BY provincia
    """)).mappings().all()

    return {"ok": True, "message": None, "data": [dict(r) for r in rows]}


from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {"ok": True, "message": "UP", "data": {"status": "running"}}

@router.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    value = db.execute(text("SELECT 1")).scalar()
    return {"ok": True, "message": "DB OK", "data": {"select_1": value}}
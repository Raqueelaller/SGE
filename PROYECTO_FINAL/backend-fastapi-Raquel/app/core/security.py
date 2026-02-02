from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

security = HTTPBearer(auto_error=False)

def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    # 1) comprobar que llegó algo en Authorization
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Token no enviado")

    # 2) credentials.scheme será "Bearer" y credentials.credentials el token
    token = credentials.credentials.strip()

    # 3) validar contra BD
    row = db.execute(
        text("""
            SELECT id_usuario, usuario, id_rol
            FROM sgi_usuarios
            WHERE token_sesion = :t
            LIMIT 1
        """),
        {"t": token},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Token inválido")

    return {"id_usuario": row[0], "usuario": row[1], "id_rol": row[2]}

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException

from app.db.session import get_db
from app.core.security import require_token

from sqlalchemy.exc import IntegrityError
from app.schemas.alumnos import AlumnoCreate
from app.schemas.alumnos import AlumnoUpdate



def validar_entidad_es_centro_educativo(db: Session, id_entidad: int) -> None:
    # 1) obtener el id del tipo "CENTRO EDUCATIVO"
    id_tipo_centro = db.execute(text("""
        SELECT id_tipo_entidad
        FROM sgi_tipos_entidad
        WHERE UPPER(tipo_entidad) = 'CENTRO EDUCATIVO'
        LIMIT 1
    """)).scalar()

    if id_tipo_centro is None:
        # Esto significa que en tu BD no existe ese tipo (o el texto es distinto)
        raise HTTPException(status_code=500, detail="No existe el tipo 'CENTRO EDUCATIVO' en sgi_tipos_entidad")

    # 2) comprobar el tipo de la entidad elegida
    entidad_tipo = db.execute(text("""
        SELECT id_tipo_entidad
        FROM sgi_entidades
        WHERE id_entidad = :id_entidad
        LIMIT 1
    """), {"id_entidad": id_entidad}).scalar()

    if entidad_tipo is None:
        raise HTTPException(status_code=400, detail="La entidad centro no existe")

    if int(entidad_tipo) != int(id_tipo_centro):
        raise HTTPException(status_code=400, detail="La entidad seleccionada no es un CENTRO EDUCATIVO")


router = APIRouter(prefix="/alumnos", tags=["alumnos"])

@router.get("")
def listar_alumnos(
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    # JOINs para NO devolver ids de FK, sino los nombres
    
    rows = db.execute(text("""
        SELECT
            a.id_alumno,
            a.nif_nie,
            a.nombre,
            a.apellidos,
            a.fecha_nacimiento,
            a.curso,
            a.telefono,
            a.direccion,
            a.cp,
            a.localidad,
            a.observaciones,

            e.entidad AS entidad_centro,
            c.ciclo AS ciclo,
            p.provincia AS provincia,

            ev.entidad AS vacante_asignada
        FROM sgi_alumnos a
        JOIN sgi_entidades e ON e.id_entidad = a.id_entidad_centro
        JOIN sgi_ciclos c ON c.id_ciclo = a.id_ciclo
        LEFT JOIN sgi_provincias p ON p.id_provincia = a.id_provincia
        LEFT JOIN sgi_vacantes_x_alumnos vxa ON vxa.id_alumno = a.id_alumno
        LEFT JOIN sgi_vacantes v ON v.id_vacante = vxa.id_vacante
        LEFT JOIN sgi_entidades ev ON ev.id_entidad = v.id_entidad
        ORDER BY a.apellidos, a.nombre
    """)).mappings().all()


    data = [dict(r) for r in rows]

    return {"ok": True, "message": "Listado de alumnos", "data": data}

@router.get("/{id_alumno}")
def obtener_alumno(
    id_alumno: int,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    row = db.execute(text("""
        SELECT
            a.id_alumno,
            a.nif_nie,
            a.nombre,
            a.apellidos,
            a.fecha_nacimiento,
            a.id_entidad_centro,
            a.id_ciclo,
            a.curso,
            a.telefono,
            a.direccion,
            a.cp,
            a.localidad,
            a.id_provincia,
            a.observaciones,

            e.entidad AS entidad_centro,
            c.ciclo AS ciclo,
            p.provincia AS provincia,

            ev.entidad AS vacante_asignada
        FROM sgi_alumnos a
        JOIN sgi_entidades e ON e.id_entidad = a.id_entidad_centro
        JOIN sgi_ciclos c ON c.id_ciclo = a.id_ciclo
        LEFT JOIN sgi_provincias p ON p.id_provincia = a.id_provincia
        LEFT JOIN sgi_vacantes_x_alumnos vxa ON vxa.id_alumno = a.id_alumno
        LEFT JOIN sgi_vacantes v ON v.id_vacante = vxa.id_vacante
        LEFT JOIN sgi_entidades ev ON ev.id_entidad = v.id_entidad
        WHERE a.id_alumno = :id
        LIMIT 1
    """), {"id": id_alumno}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    return {"ok": True, "message": "Detalle de alumno", "data": dict(row)}



@router.post("")
def crear_alumno(
    payload: AlumnoCreate,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    validar_entidad_es_centro_educativo(db, payload.id_entidad_centro)

    try:
        db.execute(text("""
            INSERT INTO sgi_alumnos (
                nif_nie, nombre, apellidos, fecha_nacimiento,
                id_entidad_centro, id_ciclo, curso, telefono,
                direccion, cp, localidad, id_provincia, observaciones
            ) VALUES (
                :nif_nie, :nombre, :apellidos, :fecha_nacimiento,
                :id_entidad_centro, :id_ciclo, :curso, :telefono,
                :direccion, :cp, :localidad, :id_provincia, :observaciones
            )
        """), payload.model_dump())
        db.commit()

    except IntegrityError as e:
        db.rollback()
        # lo más típico: nif_nie duplicado (UNIQUE)
        return {"ok": False, "message": "No se pudo crear (NIF/NIE duplicado u otra restricción)", "data": None}

    return {"ok": True, "message": "Alumno creado", "data": None}


@router.put("/{id_alumno}")
def actualizar_alumno(
    id_alumno: int,
    payload: AlumnoUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    # 1) comprobar que existe
    existe = db.execute(text("""
        SELECT id_alumno
        FROM sgi_alumnos
        WHERE id_alumno = :id
        LIMIT 1
    """), {"id": id_alumno}).scalar()

    if not existe:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    # 2) validar que la entidad es centro educativo
    validar_entidad_es_centro_educativo(db, payload.id_entidad_centro)

    # 3) update
    try:
        params = payload.model_dump()
        params["id_alumno"] = id_alumno

        db.execute(text("""
            UPDATE sgi_alumnos
            SET
                nif_nie = :nif_nie,
                nombre = :nombre,
                apellidos = :apellidos,
                fecha_nacimiento = :fecha_nacimiento,
                id_entidad_centro = :id_entidad_centro,
                id_ciclo = :id_ciclo,
                curso = :curso,
                telefono = :telefono,
                direccion = :direccion,
                cp = :cp,
                localidad = :localidad,
                id_provincia = :id_provincia,
                observaciones = :observaciones
            WHERE id_alumno = :id_alumno
        """), params)

        db.commit()

    except IntegrityError:
        db.rollback()
        return {"ok": False, "message": "No se pudo actualizar (NIF/NIE duplicado u otra restricción)", "data": None}

    return {"ok": True, "message": "Alumno actualizado", "data": None}

@router.delete("/{id_alumno}")
def borrar_alumno(
    id_alumno: int,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    # 1) comprobar que existe
    existe = db.execute(text("""
        SELECT id_alumno
        FROM sgi_alumnos
        WHERE id_alumno = :id
        LIMIT 1
    """), {"id": id_alumno}).scalar()

    if not existe:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    # 2) comprobar si está asignado a una vacante
    asignado = db.execute(text("""
        SELECT id_vacante_x_alumno
        FROM sgi_vacantes_x_alumnos
        WHERE id_alumno = :id
        LIMIT 1
    """), {"id": id_alumno}).scalar()

    if asignado:
        raise HTTPException(
            status_code=400,
            detail="No se puede borrar: el alumno está asignado a una vacante. Desasígnalo primero."
        )

    # 3) borrar
    db.execute(text("""
        DELETE FROM sgi_alumnos
        WHERE id_alumno = :id
    """), {"id": id_alumno})
    db.commit()

    return {"ok": True, "message": "Alumno eliminado", "data": None}

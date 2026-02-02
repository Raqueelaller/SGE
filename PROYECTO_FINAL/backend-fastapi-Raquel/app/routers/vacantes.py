from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.db.session import get_db
from app.core.security import require_token

from app.schemas.vacantes import VacanteCreate
from app.schemas.vacantes import VacanteUpdate




router = APIRouter(prefix="/vacantes", tags=["vacantes"])

@router.get("")
def listar_vacantes(
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    rows = db.execute(text("""
        SELECT
            v.id_vacante,
            v.curso,
            v.num_vacantes,
            v.observaciones,

            e.entidad AS entidad,
            c.ciclo AS ciclo,

            COUNT(vxa.id_alumno) AS num_alumnos,

            GROUP_CONCAT(CONCAT(a.nombre, ' ', a.apellidos) ORDER BY a.apellidos SEPARATOR ', ') AS listado_alumnos
        FROM sgi_vacantes v
        JOIN sgi_entidades e ON e.id_entidad = v.id_entidad
        JOIN sgi_ciclos c ON c.id_ciclo = v.id_ciclo
        LEFT JOIN sgi_vacantes_x_alumnos vxa ON vxa.id_vacante = v.id_vacante
        LEFT JOIN sgi_alumnos a ON a.id_alumno = vxa.id_alumno
        GROUP BY
            v.id_vacante, v.curso, v.num_vacantes, v.observaciones, e.entidad, c.ciclo
        ORDER BY
            e.entidad, c.ciclo, v.curso
    """)).mappings().all()

    data = []
    for r in rows:
        d = dict(r)
        # si no hay alumnos, GROUP_CONCAT devuelve None -> lo dejamos en "" para el grid
        if d["listado_alumnos"] is None:
            d["listado_alumnos"] = ""
        data.append(d)

    return {"ok": True, "message": "Listado de vacantes", "data": data}

@router.post("")
def crear_vacante(
    payload: VacanteCreate,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    try:
        db.execute(text("""
            INSERT INTO sgi_vacantes (
                id_entidad, id_ciclo, curso, num_vacantes, observaciones
            ) VALUES (
                :id_entidad, :id_ciclo, :curso, :num_vacantes, :observaciones
            )
        """), payload.model_dump())
        db.commit()

    except IntegrityError:
        db.rollback()
        return {
            "ok": False,
            "message": "No se pudo crear: ya existe una vacante para esa entidad, ciclo y curso (UNIQUE).",
            "data": None
        }

    return {"ok": True, "message": "Vacante creada", "data": None}


@router.get("/{id_vacante}/alumnos-disponibles")
def alumnos_disponibles(
    id_vacante: int,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    # 1) obtener ciclo y curso de la vacante
    vac = db.execute(text("""
        SELECT id_ciclo, curso
        FROM sgi_vacantes
        WHERE id_vacante = :id
        LIMIT 1
    """), {"id": id_vacante}).mappings().first()

    if not vac:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    # 2) alumnos del mismo ciclo+curso que NO estén asignados en la tabla auxiliar
    rows = db.execute(text("""
        SELECT
            a.id_alumno,
            a.nombre,
            a.apellidos,
            a.nif_nie
        FROM sgi_alumnos a
        LEFT JOIN sgi_vacantes_x_alumnos vxa ON vxa.id_alumno = a.id_alumno
        WHERE a.id_ciclo = :id_ciclo
          AND a.curso = :curso
          AND vxa.id_alumno IS NULL
        ORDER BY a.apellidos, a.nombre
    """), {"id_ciclo": vac["id_ciclo"], "curso": vac["curso"]}).mappings().all()

    data = [dict(r) for r in rows]
    return {"ok": True, "message": "Alumnos disponibles", "data": data}


@router.post("/{id_vacante}/alumnos/{id_alumno}")
def asignar_alumno(
    id_vacante: int,
    id_alumno: int,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    # 1) vacante existe + datos necesarios
    vac = db.execute(text("""
        SELECT id_vacante, id_ciclo, curso, num_vacantes
        FROM sgi_vacantes
        WHERE id_vacante = :id
        LIMIT 1
    """), {"id": id_vacante}).mappings().first()

    if not vac:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    # 2) alumno existe + datos necesarios
    alum = db.execute(text("""
        SELECT id_alumno, id_ciclo, curso
        FROM sgi_alumnos
        WHERE id_alumno = :id
        LIMIT 1
    """), {"id": id_alumno}).mappings().first()

    if not alum:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    # 3) compatibilidad ciclo+curso
    if int(alum["id_ciclo"]) != int(vac["id_ciclo"]) or int(alum["curso"]) != int(vac["curso"]):
        raise HTTPException(status_code=400, detail="El alumno no coincide en ciclo y/o curso con la vacante")

    # 4) alumno ya asignado a otra vacante
    ya = db.execute(text("""
        SELECT id_vacante
        FROM sgi_vacantes_x_alumnos
        WHERE id_alumno = :id_alumno
        LIMIT 1
    """), {"id_alumno": id_alumno}).scalar()

    if ya:
        raise HTTPException(status_code=400, detail="El alumno ya está asignado a una vacante")

    # 5) capacidad: no superar num_vacantes
    ocupadas = db.execute(text("""
        SELECT COUNT(*) 
        FROM sgi_vacantes_x_alumnos
        WHERE id_vacante = :id_vacante
    """), {"id_vacante": id_vacante}).scalar()

    if int(ocupadas) >= int(vac["num_vacantes"]):
        raise HTTPException(status_code=400, detail="No hay plazas disponibles en esta vacante")

    # 6) insertar en tabla auxiliar
    db.execute(text("""
        INSERT INTO sgi_vacantes_x_alumnos (id_vacante, id_alumno)
        VALUES (:id_vacante, :id_alumno)
    """), {"id_vacante": id_vacante, "id_alumno": id_alumno})
    db.commit()

    return {"ok": True, "message": "Alumno asignado a la vacante", "data": None}


@router.delete("/{id_vacante}/alumnos/{id_alumno}")
def desasignar_alumno(
    id_vacante: int,
    id_alumno: int,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    # 1) comprobar que la relación existe
    rel = db.execute(text("""
        SELECT id_vacante_x_alumno
        FROM sgi_vacantes_x_alumnos
        WHERE id_vacante = :id_vacante
          AND id_alumno = :id_alumno
        LIMIT 1
    """), {"id_vacante": id_vacante, "id_alumno": id_alumno}).scalar()

    if not rel:
        raise HTTPException(status_code=404, detail="El alumno no está asignado a esta vacante")

    # 2) borrar relación
    db.execute(text("""
        DELETE FROM sgi_vacantes_x_alumnos
        WHERE id_vacante = :id_vacante
          AND id_alumno = :id_alumno
    """), {"id_vacante": id_vacante, "id_alumno": id_alumno})
    db.commit()

    return {"ok": True, "message": "Alumno desasignado de la vacante", "data": None}

@router.put("/{id_vacante}")
def actualizar_vacante(
    id_vacante: int,
    payload: VacanteUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    # 1) comprobar que existe
    existe = db.execute(text("""
        SELECT id_vacante
        FROM sgi_vacantes
        WHERE id_vacante = :id
        LIMIT 1
    """), {"id": id_vacante}).scalar()

    if not existe:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    # 2) contar alumnos asignados
    ocupadas = db.execute(text("""
        SELECT COUNT(*)
        FROM sgi_vacantes_x_alumnos
        WHERE id_vacante = :id_vacante
    """), {"id_vacante": id_vacante}).scalar()

    # 3) regla: no bajar num_vacantes por debajo de ocupadas
    if int(payload.num_vacantes) < int(ocupadas):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede poner num_vacantes={payload.num_vacantes} porque ya hay {ocupadas} alumnos asignados"
        )

    # 4) update (ojo con UNIQUE entidad+ciclo+curso)
    try:
        params = payload.model_dump()
        params["id_vacante"] = id_vacante

        db.execute(text("""
            UPDATE sgi_vacantes
            SET
                id_entidad = :id_entidad,
                id_ciclo = :id_ciclo,
                curso = :curso,
                num_vacantes = :num_vacantes,
                observaciones = :observaciones
            WHERE id_vacante = :id_vacante
        """), params)

        db.commit()

    except IntegrityError:
        db.rollback()
        return {
            "ok": False,
            "message": "No se pudo actualizar: ya existe otra vacante con esa entidad, ciclo y curso (UNIQUE).",
            "data": None
        }

    return {"ok": True, "message": "Vacante actualizada", "data": None}

@router.delete("/{id_vacante}")
def borrar_vacante(
    id_vacante: int,
    db: Session = Depends(get_db),
    user=Depends(require_token),
):
    # 1) comprobar que existe
    existe = db.execute(text("""
        SELECT id_vacante
        FROM sgi_vacantes
        WHERE id_vacante = :id
        LIMIT 1
    """), {"id": id_vacante}).scalar()

    if not existe:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    # 2) comprobar si tiene alumnos asignados
    ocupadas = db.execute(text("""
        SELECT COUNT(*)
        FROM sgi_vacantes_x_alumnos
        WHERE id_vacante = :id
    """), {"id": id_vacante}).scalar()

    if int(ocupadas) > 0:
        raise HTTPException(
            status_code=400,
            detail="No se puede borrar la vacante porque tiene alumnos asignados. Desasígnalos primero."
        )

    # 3) borrar vacante
    db.execute(text("""
        DELETE FROM sgi_vacantes
        WHERE id_vacante = :id
    """), {"id": id_vacante})
    db.commit()

    return {"ok": True, "message": "Vacante eliminada", "data": None}

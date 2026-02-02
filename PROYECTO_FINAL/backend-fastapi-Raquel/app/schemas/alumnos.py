from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

#con esto fastApi valida automáticamente el Json de entrada
class AlumnoCreate(BaseModel):
    nif_nie: str = Field(min_length=3, max_length=15)
    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=150)
    fecha_nacimiento: date
    id_entidad_centro: int
    id_ciclo: int
    curso: int = Field(ge=1, le=2)  # en FP suelen ser 1 o 2
    telefono: str = Field(min_length=3, max_length=20)

    direccion: Optional[str] = Field(default=None, max_length=150)
    cp: Optional[str] = Field(default=None, max_length=10)
    localidad: Optional[str] = Field(default=None, max_length=80)
    id_provincia: Optional[int] = None
    observaciones: Optional[str] = None

class AlumnoUpdate(AlumnoCreate):
    # de momento reutilizamos los mismos campos obligatorios que create
    # (luego si quieres hacemos update parcial con Optional)
    pass

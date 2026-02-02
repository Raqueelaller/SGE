from pydantic import BaseModel, Field
from typing import Optional

class VacanteCreate(BaseModel):
    id_entidad: int
    id_ciclo: int
    curso: int = Field(ge=1, le=2)
    num_vacantes: int = Field(ge=0)
    observaciones: Optional[str] = None

class VacanteUpdate(VacanteCreate):
    pass

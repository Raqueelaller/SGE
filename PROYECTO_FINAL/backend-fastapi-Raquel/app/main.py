from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.health import router as health_router
from app.routers.private_test import router as private_router
from app.routers.alumnos import router as alumnos_router
from app.routers.vacantes import router as vacantes_router

app = FastAPI(title="SGE API (FastAPI)")

# CORS: permite que el frontend (Angular) pueda llamar al backend desde el navegador
# Angular normalmente corre en http://localhost:4200
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT, DELETE...
    allow_headers=["*"],   # Authorization, Content-Type...
)

app.include_router(health_router)
app.include_router(private_router)
app.include_router(alumnos_router)
app.include_router(vacantes_router)

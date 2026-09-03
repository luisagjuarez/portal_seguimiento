from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_catalogos import router as catalogos_router
from app.api.routes_comentarios import router as comentarios_router
from app.api.routes_direccion_general import router as direccion_general_router
from app.api.routes_inicio import router as inicio_router
from app.api.routes_monitor import router as monitor_router
from app.api.routes_notificaciones import router as notificaciones_router
from app.api.routes_solicitudes import router as solicitudes_router
from app.api.routes_tarea_por_hacer import router as tarea_por_hacer_router
from app.api.routes_tareas import router as tareas_router
from app.api.routes_usuarios import router as usuarios_router
from app.config import settings

app = FastAPI(title="Portal DOVELA API", version="1.9.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(solicitudes_router)
app.include_router(catalogos_router)
app.include_router(tareas_router)
app.include_router(comentarios_router)
app.include_router(tarea_por_hacer_router)
app.include_router(monitor_router)
app.include_router(direccion_general_router)
app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(notificaciones_router)
app.include_router(inicio_router)

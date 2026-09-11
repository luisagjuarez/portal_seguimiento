from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_carga_equipo import router as carga_equipo_router
from app.api.routes_catalogos import router as catalogos_router
from app.api.routes_comentarios import router as comentarios_router
from app.api.routes_direccion_general import router as direccion_general_router
from app.api.routes_inicio import router as inicio_router
from app.api.routes_notificaciones import router as notificaciones_router
from app.api.routes_plantillas_solicitud import router as plantillas_solicitud_router
from app.api.routes_solicitudes import router as solicitudes_router
from app.api.routes_tarea_por_hacer import router as tarea_por_hacer_router
from app.api.routes_tareas import router as tareas_router
from app.api.routes_usuarios import router as usuarios_router
from app.config import settings
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)

INTERVALO_ALERTAS_SIN_TAREA_SEGUNDOS = 600  # 10 minutos


def _ejecutar_sincronizacion_alertas() -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        repository.sincronizar_alertas_sin_tarea_activa(cursor)
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        raise
    finally:
        release_connection(db_conn)


async def _loop_alertas_sin_tarea_activa() -> None:
    """Vista "Carga del equipo": cada 10 min revisa quién (Team/Scrum Master) se quedó sin
    tarea En progreso y notifica una sola vez (dedup en `alertas_sin_tarea_activa`, ver
    `repository.sincronizar_alertas_sin_tarea_activa`)."""
    while True:
        await asyncio.sleep(INTERVALO_ALERTAS_SIN_TAREA_SEGUNDOS)
        try:
            await asyncio.to_thread(_ejecutar_sincronizacion_alertas)
        except Exception:
            logger.exception("Fallo el chequeo periódico de alertas de tarea activa")


@asynccontextmanager
async def lifespan(_: FastAPI):
    tarea_fondo = asyncio.create_task(_loop_alertas_sin_tarea_activa())
    yield
    tarea_fondo.cancel()


app = FastAPI(title="Portal DOVELA API", version="1.10.0", lifespan=lifespan)

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
app.include_router(direccion_general_router)
app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(notificaciones_router)
app.include_router(inicio_router)
app.include_router(carga_equipo_router)
app.include_router(plantillas_solicitud_router)

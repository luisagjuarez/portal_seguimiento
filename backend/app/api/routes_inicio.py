from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.api.schemas import InicioResumenOut, ResumenBloque
from app.auth.dependencies import UsuarioActual, get_current_user
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

ROLES_CON_VISTA_GERENCIAL = {"SCRUM MASTER", "PRODUCT OWNER"}


@router.get("/inicio/resumen", response_model=InicioResumenOut)
def obtener_resumen_inicio(usuario_actual: UsuarioActual = Depends(get_current_user)) -> InicioResumenOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        if usuario_actual.codigo_rol_scrum in ROLES_CON_VISTA_GERENCIAL:
            return InicioResumenOut(
                solicitudes_totales=ResumenBloque(**repository.get_resumen_solicitudes(cursor)),
                tareas_totales=ResumenBloque(**repository.get_resumen_tareas(cursor)),
            )
        return InicioResumenOut(
            mis_solicitudes=ResumenBloque(
                **repository.get_resumen_solicitudes(cursor, solicitante_id=usuario_actual.id)
            ),
            solicitudes_responsable=ResumenBloque(
                **repository.get_resumen_solicitudes(cursor, responsable_atencion_id=usuario_actual.id)
            ),
            mis_tareas=ResumenBloque(**repository.get_resumen_tareas(cursor, responsable_id=usuario_actual.id)),
        )
    finally:
        release_connection(db_conn)

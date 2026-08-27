from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends

from app.api.schemas import MonitorKpisOut
from app.auth.dependencies import UsuarioActual, require_scrum_master_or_product_owner
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/monitor/kpis", response_model=MonitorKpisOut)
def obtener_monitor_kpis(
    _: UsuarioActual = Depends(require_scrum_master_or_product_owner),
) -> MonitorKpisOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        hoy = date.today()
        kpis = MonitorKpisOut(
            vencidas=repository.list_tareas_vencidas(cursor, hoy),
            por_vencer=repository.list_tareas_por_vencer(cursor, hoy),
            carga_por_responsable=repository.list_carga_por_responsable(cursor),
            distribucion_estatus=repository.list_distribucion_estatus(cursor),
            cumplimiento=repository.get_cumplimiento_planeado_real(cursor),
        )
    finally:
        release_connection(db_conn)
    return kpis

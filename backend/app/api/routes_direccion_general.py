from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import DireccionGeneralKpisOut
from app.auth.dependencies import UsuarioActual, require_scrum_master_or_product_owner
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/direccion-general/kpis", response_model=DireccionGeneralKpisOut)
def obtener_direccion_general_kpis(
    desde: date = Query(...),
    hasta: date = Query(...),
    _: UsuarioActual = Depends(require_scrum_master_or_product_owner),
) -> DireccionGeneralKpisOut:
    if hasta < desde:
        raise HTTPException(status_code=400, detail="hasta no puede ser anterior a desde")

    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        kpis = DireccionGeneralKpisOut(
            totales=repository.get_direccion_general_totales(cursor, desde, hasta),
            por_cliente=repository.list_direccion_general_por_cliente(cursor, desde, hasta),
            por_tipo=repository.list_direccion_general_por_tipo(cursor, desde, hasta),
            por_area=repository.list_direccion_general_por_area(cursor, desde, hasta),
            solicitudes_por_estatus=repository.list_distribucion_estatus_solicitud(cursor),
            tareas_por_estatus=repository.list_distribucion_estatus(cursor),
        )
    finally:
        release_connection(db_conn)
    return kpis

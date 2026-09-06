from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas import CargaEquipoAreaOut
from app.auth.dependencies import UsuarioActual, require_no_externo
from app.db import repository
from app.db.connection import get_connection, release_connection

router = APIRouter(prefix="/api")


@router.get("/carga-equipo", response_model=list[CargaEquipoAreaOut])
def obtener_carga_equipo(
    _: UsuarioActual = Depends(require_no_externo),
) -> list[CargaEquipoAreaOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        areas = repository.get_carga_equipo(cursor)
    finally:
        release_connection(db_conn)
    return [CargaEquipoAreaOut(**area) for area in areas]

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import NotificacionesNoLeidasCountOut, NotificacionOut
from app.auth.dependencies import UsuarioActual, get_current_user
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/notificaciones", response_model=list[NotificacionOut])
def listar_notificaciones(
    solo_no_leidas: bool = Query(default=False),
    usuario_actual: UsuarioActual = Depends(get_current_user),
) -> list[NotificacionOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_notificaciones_by_destinatario(
            cursor, usuario_actual.id, solo_no_leidas=solo_no_leidas
        )
    finally:
        release_connection(db_conn)
    return [NotificacionOut(**fila) for fila in filas]


@router.get("/notificaciones/no-leidas/count", response_model=NotificacionesNoLeidasCountOut)
def contar_notificaciones_no_leidas(
    usuario_actual: UsuarioActual = Depends(get_current_user),
) -> NotificacionesNoLeidasCountOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        no_leidas = repository.count_no_leidas(cursor, usuario_actual.id)
    finally:
        release_connection(db_conn)
    return NotificacionesNoLeidasCountOut(no_leidas=no_leidas)


@router.put("/notificaciones/{notificacion_id}/leer", status_code=204)
def marcar_notificacion_leida(
    notificacion_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.marcar_notificacion_leida(cursor, notificacion_id, usuario_actual.id)
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Notificación no encontrada")
        db_conn.commit()
    except HTTPException:
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error marcando notificación %s como leída", notificacion_id)
        raise HTTPException(status_code=500, detail="No se pudo marcar la notificación") from None
    finally:
        release_connection(db_conn)


@router.put("/notificaciones/leer-todas", status_code=204)
def marcar_todas_notificaciones_leidas(usuario_actual: UsuarioActual = Depends(get_current_user)) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        repository.marcar_todas_notificaciones_leidas(cursor, usuario_actual.id)
        db_conn.commit()
    except Exception:
        db_conn.rollback()
        logger.exception("Error marcando todas las notificaciones como leídas")
        raise HTTPException(status_code=500, detail="No se pudieron marcar las notificaciones") from None
    finally:
        release_connection(db_conn)

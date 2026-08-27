from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import PorHacerOut, PorHacerUpdate
from app.auth.dependencies import UsuarioActual, get_current_user, require_autor_o_scrum_master
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.put("/tarea-por-hacer/{item_id}", response_model=PorHacerOut)
def actualizar_por_hacer(
    item_id: int, body: PorHacerUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> PorHacerOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        item_actual = repository.get_por_hacer_by_id(cursor, item_id)
        if item_actual is None:
            raise HTTPException(status_code=404, detail="Ítem no encontrado")
        require_autor_o_scrum_master(usuario_actual, item_actual["creado_por"])

        repository.update_por_hacer(
            cursor,
            item_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            responsable_id=body.responsable_id,
            esta_completa=body.esta_completa,
            actor=usuario_actual.usuario,
        )
        fila = repository.get_por_hacer_by_id(cursor, item_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error actualizando ítem por hacer %s", item_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar el ítem") from None
    finally:
        release_connection(db_conn)

    return PorHacerOut(**fila)


@router.delete("/tarea-por-hacer/{item_id}", status_code=204)
def borrar_por_hacer(item_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        item_actual = repository.get_por_hacer_by_id(cursor, item_id)
        if item_actual is None:
            raise HTTPException(status_code=404, detail="Ítem no encontrado")
        require_autor_o_scrum_master(usuario_actual, item_actual["creado_por"])

        repository.delete_por_hacer(cursor, item_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error borrando ítem por hacer %s", item_id)
        raise HTTPException(status_code=500, detail="No se pudo borrar el ítem") from None
    finally:
        release_connection(db_conn)

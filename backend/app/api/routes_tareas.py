from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.api.schemas import TareaCreateUpdate, TareaOut
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.put("/tareas/{tarea_id}", response_model=TareaOut)
def actualizar_tarea(tarea_id: int, body: TareaCreateUpdate) -> TareaOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.update_tarea(
            cursor,
            tarea_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            responsable_id=body.responsable_id,
            esta_completa=body.esta_completa,
        )
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        fila = repository.get_tarea_by_id(cursor, tarea_id)
        db_conn.commit()
    except HTTPException:
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error actualizando tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar la tarea") from None
    finally:
        release_connection(db_conn)

    return TareaOut(**fila)


@router.delete("/tareas/{tarea_id}", status_code=204)
def borrar_tarea(tarea_id: int) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.delete_tarea(cursor, tarea_id)
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        db_conn.commit()
    except HTTPException:
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error borrando tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudo borrar la tarea") from None
    finally:
        release_connection(db_conn)

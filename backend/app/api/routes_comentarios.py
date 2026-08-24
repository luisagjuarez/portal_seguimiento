from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import ComentarioCreateUpdate, ComentarioOut
from app.auth.dependencies import UsuarioActual, get_current_user
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.put("/comentarios/{comentario_id}", response_model=ComentarioOut)
def actualizar_comentario(
    comentario_id: int, body: ComentarioCreateUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> ComentarioOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.update_comentario(
            cursor, comentario_id, texto=body.texto_comentario, actor=usuario_actual.usuario
        )
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Comentario no encontrado")

        fila = repository.get_comentario_by_id(cursor, comentario_id)
        db_conn.commit()
    except HTTPException:
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error actualizando comentario %s", comentario_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar el comentario") from None
    finally:
        release_connection(db_conn)

    return ComentarioOut(**fila)


@router.delete("/comentarios/{comentario_id}", status_code=204)
def borrar_comentario(comentario_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.delete_comentario(cursor, comentario_id, actor=usuario_actual.usuario)
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Comentario no encontrado")
        db_conn.commit()
    except HTTPException:
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error borrando comentario %s", comentario_id)
        raise HTTPException(status_code=500, detail="No se pudo borrar el comentario") from None
    finally:
        release_connection(db_conn)

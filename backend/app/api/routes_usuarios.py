from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import ActualizarAccesoRequest, MiembroAccesoOut, OtorgarAccesoRequest
from app.auth.dependencies import UsuarioActual, require_scrum_master
from app.auth.security import hash_password
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/usuarios")


@router.get("", response_model=list[MiembroAccesoOut])
def listar_usuarios(_: UsuarioActual = Depends(require_scrum_master)) -> list[MiembroAccesoOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_miembros_con_acceso(cursor)
    finally:
        release_connection(db_conn)
    return [MiembroAccesoOut(**fila) for fila in filas]


@router.post("/{miembro_id}/acceso", response_model=MiembroAccesoOut, status_code=201)
def otorgar_acceso(
    miembro_id: int,
    body: OtorgarAccesoRequest,
    _: UsuarioActual = Depends(require_scrum_master),
) -> MiembroAccesoOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        miembro = repository.get_miembro_by_id(cursor, miembro_id)
        if miembro is None:
            raise HTTPException(status_code=404, detail="Miembro del equipo no encontrado")
        if miembro["acceso_activo"]:
            raise HTTPException(
                status_code=409, detail="Este miembro ya tiene acceso; usa editar en vez de otorgar"
            )

        repository.otorgar_acceso_miembro(
            cursor, miembro_id, hash_password(body.password), body.codigo_rol_scrum
        )
        filas = repository.list_miembros_con_acceso(cursor)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error otorgando acceso al miembro %s", miembro_id)
        raise HTTPException(status_code=500, detail="No se pudo otorgar el acceso") from None
    finally:
        release_connection(db_conn)

    actualizado = next(f for f in filas if f["id"] == miembro_id)
    return MiembroAccesoOut(**actualizado)


@router.put("/{miembro_id}/acceso", response_model=MiembroAccesoOut)
def actualizar_acceso(
    miembro_id: int,
    body: ActualizarAccesoRequest,
    _: UsuarioActual = Depends(require_scrum_master),
) -> MiembroAccesoOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        password_hash = hash_password(body.password) if body.password else None
        filas_afectadas = repository.actualizar_acceso_miembro(
            cursor, miembro_id, body.codigo_rol_scrum, body.acceso_activo, password_hash
        )
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Miembro del equipo no encontrado")

        filas = repository.list_miembros_con_acceso(cursor)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error actualizando acceso del miembro %s", miembro_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar el acceso") from None
    finally:
        release_connection(db_conn)

    actualizado = next(f for f in filas if f["id"] == miembro_id)
    return MiembroAccesoOut(**actualizado)

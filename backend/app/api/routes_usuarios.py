from __future__ import annotations

import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    ActualizarMiembroRequest,
    CrearMiembroRequest,
    MiembroAccesoOut,
    OtorgarAccesoRequest,
)
from app.auth.dependencies import UsuarioActual, require_scrum_master
from app.auth.security import hash_password
from app.db import repository
from app.db.connection import get_connection, release_connection

_ERROR_DUPLICADO = "Ya existe un miembro con ese usuario o correo"

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


@router.post("", response_model=MiembroAccesoOut, status_code=201)
def crear_usuario(
    body: CrearMiembroRequest,
    usuario_actual: UsuarioActual = Depends(require_scrum_master),
) -> MiembroAccesoOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        try:
            miembro_id = repository.crear_miembro(
                cursor, body.usuario, body.nombre_completo, body.correo_electronico,
                actor=usuario_actual.usuario,
            )
        except psycopg.errors.UniqueViolation:
            db_conn.rollback()
            raise HTTPException(status_code=409, detail=_ERROR_DUPLICADO) from None

        filas = repository.list_miembros_con_acceso(cursor)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando miembro")
        raise HTTPException(status_code=500, detail="No se pudo crear el miembro") from None
    finally:
        release_connection(db_conn)

    creado = next(f for f in filas if f["id"] == miembro_id)
    return MiembroAccesoOut(**creado)


@router.put("/{miembro_id}", response_model=MiembroAccesoOut)
def actualizar_usuario(
    miembro_id: int,
    body: ActualizarMiembroRequest,
    usuario_actual: UsuarioActual = Depends(require_scrum_master),
) -> MiembroAccesoOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        password_hash = hash_password(body.password) if body.password else None
        try:
            filas_afectadas = repository.actualizar_miembro(
                cursor, miembro_id, body.usuario, body.nombre_completo, body.correo_electronico,
                body.codigo_rol_scrum, body.acceso_activo, password_hash,
                actor=usuario_actual.usuario,
            )
        except psycopg.errors.UniqueViolation:
            db_conn.rollback()
            raise HTTPException(status_code=409, detail=_ERROR_DUPLICADO) from None
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
        logger.exception("Error actualizando miembro %s", miembro_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar el miembro") from None
    finally:
        release_connection(db_conn)

    actualizado = next(f for f in filas if f["id"] == miembro_id)
    return MiembroAccesoOut(**actualizado)


@router.delete("/{miembro_id}", status_code=204)
def dar_de_baja_usuario(
    miembro_id: int,
    usuario_actual: UsuarioActual = Depends(require_scrum_master),
) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.dar_de_baja_miembro(cursor, miembro_id, actor=usuario_actual.usuario)
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Miembro del equipo no encontrado")
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error dando de baja al miembro %s", miembro_id)
        raise HTTPException(status_code=500, detail="No se pudo dar de baja al miembro") from None
    finally:
        release_connection(db_conn)

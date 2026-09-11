from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    PlantillaSolicitudCreateUpdate,
    PlantillaSolicitudDetalleOut,
    PlantillaSolicitudResumenOut,
)
from app.auth.dependencies import UsuarioActual, get_current_user, require_scrum_master
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/plantillas-solicitud")


def _validar_tareas_sin_responsable_externo(cursor, tareas: list) -> None:
    """Falla temprano al guardar la plantilla (no al generar tareas): un Externo nunca puede
    ser responsable de tarea, igual que en la creación manual de tareas (Punto 1, 2026-09-04)."""
    for tarea in tareas:
        if tarea.responsable_id and repository.es_miembro_externo(cursor, tarea.responsable_id):
            raise HTTPException(
                status_code=422,
                detail=f"La tarea '{tarea.nombre}' no puede tener un responsable Externo",
            )


def _validar_tipo_solicitud_existe(cursor, tipo_solicitud_id: int) -> None:
    tipos = repository.list_tipos_solicitud(cursor)
    if not any(t["id"] == tipo_solicitud_id for t in tipos):
        raise HTTPException(status_code=404, detail="Tipo de solicitud no encontrado")


@router.get("", response_model=list[PlantillaSolicitudResumenOut])
def listar_plantillas_solicitud(
    incluir_inactivas: bool = False,
    usuario_actual: UsuarioActual = Depends(get_current_user),
) -> list[PlantillaSolicitudResumenOut]:
    # Defensa en profundidad: solo el Scrum Master puede ver las inactivas, sin importar lo
    # que mande el query param.
    solo_activas = not (incluir_inactivas and usuario_actual.codigo_rol_scrum == "SCRUM MASTER")
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_plantillas_solicitud(cursor, solo_activas=solo_activas)
    finally:
        release_connection(db_conn)
    return [PlantillaSolicitudResumenOut(**fila) for fila in filas]


@router.get("/{plantilla_id}", response_model=PlantillaSolicitudDetalleOut)
def obtener_plantilla_solicitud(
    plantilla_id: int, _: UsuarioActual = Depends(require_scrum_master)
) -> PlantillaSolicitudDetalleOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        plantilla = repository.get_plantilla_solicitud_by_id(cursor, plantilla_id)
    finally:
        release_connection(db_conn)
    if plantilla is None:
        raise HTTPException(status_code=404, detail="Plantilla de solicitud no encontrada")
    return PlantillaSolicitudDetalleOut(**plantilla)


@router.post("", response_model=PlantillaSolicitudDetalleOut, status_code=201)
def crear_plantilla_solicitud(
    body: PlantillaSolicitudCreateUpdate,
    usuario_actual: UsuarioActual = Depends(require_scrum_master),
) -> PlantillaSolicitudDetalleOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        _validar_tipo_solicitud_existe(cursor, body.tipo_solicitud_id)
        _validar_tareas_sin_responsable_externo(cursor, body.tareas)

        plantilla_id = repository.insert_plantilla_solicitud(
            cursor,
            nombre=body.nombre,
            tipo_solicitud_id=body.tipo_solicitud_id,
            descripcion_default=body.descripcion_default,
            orden_prioridad_default=body.orden_prioridad_default,
            tareas=[t.model_dump() for t in body.tareas],
            actor=usuario_actual.usuario,
        )
        plantilla = repository.get_plantilla_solicitud_by_id(cursor, plantilla_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando plantilla de solicitud")
        raise HTTPException(status_code=500, detail="No se pudo crear la plantilla") from None
    finally:
        release_connection(db_conn)

    return PlantillaSolicitudDetalleOut(**plantilla)


@router.put("/{plantilla_id}", response_model=PlantillaSolicitudDetalleOut)
def actualizar_plantilla_solicitud(
    plantilla_id: int,
    body: PlantillaSolicitudCreateUpdate,
    usuario_actual: UsuarioActual = Depends(require_scrum_master),
) -> PlantillaSolicitudDetalleOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        _validar_tipo_solicitud_existe(cursor, body.tipo_solicitud_id)
        _validar_tareas_sin_responsable_externo(cursor, body.tareas)

        filas_afectadas = repository.update_plantilla_solicitud(
            cursor,
            plantilla_id,
            nombre=body.nombre,
            tipo_solicitud_id=body.tipo_solicitud_id,
            descripcion_default=body.descripcion_default,
            orden_prioridad_default=body.orden_prioridad_default,
            tareas=[t.model_dump() for t in body.tareas],
            actor=usuario_actual.usuario,
        )
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Plantilla de solicitud no encontrada")

        plantilla = repository.get_plantilla_solicitud_by_id(cursor, plantilla_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error actualizando plantilla de solicitud %s", plantilla_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar la plantilla") from None
    finally:
        release_connection(db_conn)

    return PlantillaSolicitudDetalleOut(**plantilla)


@router.delete("/{plantilla_id}", status_code=204)
def dar_de_baja_plantilla_solicitud(
    plantilla_id: int, usuario_actual: UsuarioActual = Depends(require_scrum_master)
) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.dar_de_baja_plantilla_solicitud(
            cursor, plantilla_id, actor=usuario_actual.usuario
        )
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Plantilla de solicitud no encontrada")
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error dando de baja la plantilla de solicitud %s", plantilla_id)
        raise HTTPException(status_code=500, detail="No se pudo dar de baja la plantilla") from None
    finally:
        release_connection(db_conn)

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    ComentarioCreateUpdate,
    ComentarioOut,
    EnlaceTareaCreate,
    EnlaceTareaOut,
    HitoCreateUpdate,
    HitoOut,
    PorHacerCreate,
    PorHacerOut,
    TareaCreateUpdate,
    TareaOut,
    TareaTableroOut,
)
from app.auth.dependencies import UsuarioActual, get_current_user
from app.db import repository
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/tareas", response_model=list[TareaTableroOut])
def listar_tareas(
    cliente: str = Query(default="", max_length=200),
    responsable_id: int | None = Query(default=None),
    _: UsuarioActual = Depends(get_current_user),
) -> list[TareaTableroOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_tareas(cursor, cliente=cliente or None, responsable_id=responsable_id)
    finally:
        release_connection(db_conn)
    return [TareaTableroOut(**fila) for fila in filas]


@router.get("/tareas/{tarea_id}", response_model=TareaTableroOut)
def obtener_tarea(tarea_id: int, _: UsuarioActual = Depends(get_current_user)) -> TareaTableroOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        fila = repository.get_tarea_by_id(cursor, tarea_id)
    finally:
        release_connection(db_conn)
    if fila is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return TareaTableroOut(**fila)


@router.put("/tareas/{tarea_id}", response_model=TareaOut)
def actualizar_tarea(
    tarea_id: int, body: TareaCreateUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> TareaOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.update_tarea(
            cursor,
            tarea_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            responsable_id=body.responsable_id,
            codigo_estatus_tarea=body.codigo_estatus_tarea,
            actor=usuario_actual.usuario,
            fecha_inicio=body.fecha_inicio,
            fecha_fin=body.fecha_fin,
            fecha_inicio_real=body.fecha_inicio_real,
            fecha_fin_real=body.fecha_fin_real,
            horas_estimadas=body.horas_estimadas,
            horas_reales=body.horas_reales,
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
def borrar_tarea(tarea_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.delete_tarea(cursor, tarea_id, actor=usuario_actual.usuario)
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


@router.get("/tareas/{tarea_id}/hito", response_model=HitoOut)
def obtener_hito_tarea(tarea_id: int, _: UsuarioActual = Depends(get_current_user)) -> HitoOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        fila = repository.get_hito_by_tarea(cursor, tarea_id)
    finally:
        release_connection(db_conn)
    if fila is None:
        raise HTTPException(status_code=404, detail="Esta tarea no tiene hito")
    return HitoOut(**fila)


@router.post("/tareas/{tarea_id}/hito", response_model=HitoOut, status_code=201)
def crear_hito_tarea(
    tarea_id: int, body: HitoCreateUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> HitoOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        tarea = repository.get_tarea_by_id(cursor, tarea_id)
        if tarea is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        if repository.get_hito_by_tarea(cursor, tarea_id) is not None:
            raise HTTPException(status_code=409, detail="Esta tarea ya tiene un hito; usa editar en vez de crear")

        repository.insert_hito_para_tarea(
            cursor,
            tarea_id,
            solicitud_id=tarea["solicitud_id"],
            nombre=body.nombre,
            descripcion=body.descripcion,
            fecha_vencimiento=body.fecha_vencimiento,
            actor=usuario_actual.usuario,
        )
        fila = repository.get_hito_by_tarea(cursor, tarea_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando hito para tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudo crear el hito") from None
    finally:
        release_connection(db_conn)

    return HitoOut(**fila)


@router.put("/tareas/{tarea_id}/hito", response_model=HitoOut)
def actualizar_hito_tarea(
    tarea_id: int, body: HitoCreateUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> HitoOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        hito_actual = repository.get_hito_by_tarea(cursor, tarea_id)
        if hito_actual is None:
            raise HTTPException(status_code=404, detail="Esta tarea no tiene hito")

        repository.update_hito(
            cursor,
            hito_actual["id"],
            nombre=body.nombre,
            descripcion=body.descripcion,
            fecha_vencimiento=body.fecha_vencimiento,
            actor=usuario_actual.usuario,
        )
        fila = repository.get_hito_by_tarea(cursor, tarea_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error actualizando hito de tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar el hito") from None
    finally:
        release_connection(db_conn)

    return HitoOut(**fila)


@router.delete("/tareas/{tarea_id}/hito", status_code=204)
def borrar_hito_tarea(tarea_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        hito_actual = repository.get_hito_by_tarea(cursor, tarea_id)
        if hito_actual is None:
            raise HTTPException(status_code=404, detail="Esta tarea no tiene hito")

        repository.delete_hito(cursor, hito_actual["id"], actor=usuario_actual.usuario)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error borrando hito de tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudo borrar el hito") from None
    finally:
        release_connection(db_conn)


@router.get("/tareas/{tarea_id}/comentarios", response_model=list[ComentarioOut])
def listar_comentarios_tarea(tarea_id: int, _: UsuarioActual = Depends(get_current_user)) -> list[ComentarioOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_comentarios_by_tarea(cursor, tarea_id)
    finally:
        release_connection(db_conn)
    return [ComentarioOut(**fila) for fila in filas]


@router.post("/tareas/{tarea_id}/comentarios", response_model=ComentarioOut, status_code=201)
def crear_comentario_tarea(
    tarea_id: int, body: ComentarioCreateUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> ComentarioOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        tarea = repository.get_tarea_by_id(cursor, tarea_id)
        if tarea is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        comentario_id = repository.insert_comentario(
            cursor,
            solicitud_id=tarea["solicitud_id"],
            tarea_id=tarea_id,
            texto=body.texto_comentario,
            actor=usuario_actual.usuario,
        )
        fila = repository.get_comentario_by_id(cursor, comentario_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando comentario para tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudo crear el comentario") from None
    finally:
        release_connection(db_conn)

    return ComentarioOut(**fila)


@router.get("/tareas/{tarea_id}/enlaces", response_model=list[EnlaceTareaOut])
def listar_enlaces_tarea(tarea_id: int, _: UsuarioActual = Depends(get_current_user)) -> list[EnlaceTareaOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_enlaces_by_tarea(cursor, tarea_id)
    finally:
        release_connection(db_conn)
    return [EnlaceTareaOut(**fila) for fila in filas]


@router.post("/tareas/{tarea_id}/enlaces", response_model=EnlaceTareaOut, status_code=201)
def crear_enlace_tarea(
    tarea_id: int, body: EnlaceTareaCreate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> EnlaceTareaOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        tarea = repository.get_tarea_by_id(cursor, tarea_id)
        if tarea is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        enlace_id = repository.insert_enlace_tarea(
            cursor,
            tarea_id,
            solicitud_id=tarea["solicitud_id"],
            tipo_enlace=body.tipo_enlace,
            url=body.url,
            aplicacion_id=body.aplicacion_id,
            pagina_aplicacion=body.pagina_aplicacion,
            descripcion=body.descripcion,
            actor=usuario_actual.usuario,
        )
        fila = repository.get_enlace_tarea_by_id(cursor, enlace_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando enlace para tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudo crear el enlace") from None
    finally:
        release_connection(db_conn)

    return EnlaceTareaOut(**fila)


@router.get("/tareas/{tarea_id}/por-hacer", response_model=list[PorHacerOut])
def listar_por_hacer_tarea(
    tarea_id: int, _: UsuarioActual = Depends(get_current_user)
) -> list[PorHacerOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_por_hacer_by_tarea(cursor, tarea_id)
    finally:
        release_connection(db_conn)
    return [PorHacerOut(**fila) for fila in filas]


@router.post("/tareas/{tarea_id}/por-hacer", response_model=PorHacerOut, status_code=201)
def crear_por_hacer_tarea(
    tarea_id: int, body: PorHacerCreate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> PorHacerOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        tarea = repository.get_tarea_by_id(cursor, tarea_id)
        if tarea is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        item_id = repository.insert_por_hacer(
            cursor,
            tarea_id,
            solicitud_id=tarea["solicitud_id"],
            nombre=body.nombre,
            descripcion=body.descripcion,
            responsable_id=body.responsable_id,
            actor=usuario_actual.usuario,
        )
        fila = repository.get_por_hacer_by_id(cursor, item_id)
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando ítem por hacer para tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudo crear el ítem") from None
    finally:
        release_connection(db_conn)

    return PorHacerOut(**fila)

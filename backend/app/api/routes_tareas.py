from __future__ import annotations

import logging
import os
import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api import adjuntos_helpers
from app.api.schemas import (
    AdjuntoOut,
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
from app.auth.dependencies import (
    UsuarioActual,
    require_autor_o_scrum_master,
    require_no_externo,
    require_scrum_master,
)
from app.db import repository
from app.db.connection import get_connection, release_connection
from app.storage import save_attachment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

_PATRON_MENCION = re.compile(r"@(\w+)")


def _notificar_menciones(cursor, texto: str, tarea: dict, usuario_actual: UsuarioActual) -> None:
    """Fase 1.20: @usuario notifica a ese miembro (si tiene acceso activo); @todos notifica a
    todo el equipo con acceso activo. No se notifica dos veces al mismo destinatario, incluido
    quien escribió el comentario si se menciona a sí mismo."""
    tokens = {m.group(1) for m in _PATRON_MENCION.finditer(texto)}
    if not tokens:
        return

    destinatarios_ids: set[int] = set()
    for token in tokens:
        if token.upper() == "TODOS":
            destinatarios_ids.update(repository.list_miembros_activos_ids(cursor))
            continue
        miembro = repository.find_miembro_activo_by_usuario(cursor, token)
        if miembro:
            destinatarios_ids.add(miembro["id"])

    mensaje = f"Te mencionaron en un comentario de la tarea '{tarea['nombre']}'"
    for destinatario_id in destinatarios_ids:
        repository.insert_notificacion(
            cursor,
            destinatario_id,
            tipo="MENCION_COMENTARIO",
            mensaje=mensaje,
            entidad_tipo="TAREA",
            entidad_id=tarea["id"],
        )


@router.get("/tareas", response_model=list[TareaTableroOut])
def listar_tareas(
    cliente: str = Query(default="", max_length=200),
    responsable_id: int | None = Query(default=None),
    _: UsuarioActual = Depends(require_no_externo),
) -> list[TareaTableroOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_tareas(cursor, cliente=cliente or None, responsable_id=responsable_id)
    finally:
        release_connection(db_conn)
    return [TareaTableroOut(**fila) for fila in filas]


@router.get("/tareas/{tarea_id}", response_model=TareaTableroOut)
def obtener_tarea(tarea_id: int, _: UsuarioActual = Depends(require_no_externo)) -> TareaTableroOut:
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
    tarea_id: int, body: TareaCreateUpdate, usuario_actual: UsuarioActual = Depends(require_no_externo)
) -> TareaOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        tarea_antes = repository.get_tarea_by_id(cursor, tarea_id)
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

        responsable_anterior = (tarea_antes or {}).get("responsable_id")
        if body.responsable_id and body.responsable_id != responsable_anterior:
            repository.insert_notificacion(
                cursor,
                body.responsable_id,
                tipo="TAREA_ASIGNADA",
                mensaje=f"Se te asignó la tarea '{body.nombre}'",
                entidad_tipo="TAREA",
                entidad_id=tarea_id,
            )

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
def borrar_tarea(tarea_id: int, usuario_actual: UsuarioActual = Depends(require_scrum_master)) -> None:
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
def obtener_hito_tarea(tarea_id: int, _: UsuarioActual = Depends(require_no_externo)) -> HitoOut:
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
    tarea_id: int, body: HitoCreateUpdate, usuario_actual: UsuarioActual = Depends(require_no_externo)
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
    tarea_id: int, body: HitoCreateUpdate, usuario_actual: UsuarioActual = Depends(require_no_externo)
) -> HitoOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        hito_actual = repository.get_hito_by_tarea(cursor, tarea_id)
        if hito_actual is None:
            raise HTTPException(status_code=404, detail="Esta tarea no tiene hito")
        require_autor_o_scrum_master(usuario_actual, hito_actual["creado_por"])

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
def borrar_hito_tarea(tarea_id: int, usuario_actual: UsuarioActual = Depends(require_no_externo)) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        hito_actual = repository.get_hito_by_tarea(cursor, tarea_id)
        if hito_actual is None:
            raise HTTPException(status_code=404, detail="Esta tarea no tiene hito")
        require_autor_o_scrum_master(usuario_actual, hito_actual["creado_por"])

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
def listar_comentarios_tarea(tarea_id: int, _: UsuarioActual = Depends(require_no_externo)) -> list[ComentarioOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_comentarios_by_tarea(cursor, tarea_id)
    finally:
        release_connection(db_conn)
    return [ComentarioOut(**fila) for fila in filas]


@router.post("/tareas/{tarea_id}/comentarios", response_model=ComentarioOut, status_code=201)
def crear_comentario_tarea(
    tarea_id: int, body: ComentarioCreateUpdate, usuario_actual: UsuarioActual = Depends(require_no_externo)
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
        _notificar_menciones(cursor, body.texto_comentario, tarea, usuario_actual)
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
def listar_enlaces_tarea(tarea_id: int, _: UsuarioActual = Depends(require_no_externo)) -> list[EnlaceTareaOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_enlaces_by_tarea(cursor, tarea_id)
    finally:
        release_connection(db_conn)
    return [EnlaceTareaOut(**fila) for fila in filas]


@router.post("/tareas/{tarea_id}/enlaces", response_model=EnlaceTareaOut, status_code=201)
def crear_enlace_tarea(
    tarea_id: int, body: EnlaceTareaCreate, usuario_actual: UsuarioActual = Depends(require_no_externo)
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
    tarea_id: int, _: UsuarioActual = Depends(require_no_externo)
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
    tarea_id: int, body: PorHacerCreate, usuario_actual: UsuarioActual = Depends(require_no_externo)
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
        if body.responsable_id:
            repository.insert_notificacion(
                cursor,
                body.responsable_id,
                tipo="POR_HACER_ASIGNADO",
                mensaje=f"Se te asignó el pendiente '{body.nombre}' en la tarea '{tarea['nombre']}'",
                entidad_tipo="TAREA",
                entidad_id=tarea_id,
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


@router.get("/tareas/{tarea_id}/adjuntos", response_model=list[AdjuntoOut])
def listar_adjuntos_tarea(tarea_id: int, _: UsuarioActual = Depends(require_no_externo)) -> list[AdjuntoOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_adjuntos_by_tarea(cursor, tarea_id)
    finally:
        release_connection(db_conn)
    return [AdjuntoOut(**fila) for fila in filas]


@router.post("/tareas/{tarea_id}/adjuntos", response_model=list[AdjuntoOut], status_code=201)
async def agregar_adjuntos_tarea(
    tarea_id: int,
    files: Annotated[list[UploadFile], File()] = [],
    usuario_actual: UsuarioActual = Depends(require_no_externo),
) -> list[AdjuntoOut]:
    """Fase 1.21: adjuntos en tareas, desde cero (antes no existía nada) — mismo patrón que
    solicitudes, tanto al crear como para agregar después."""
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        if repository.get_tarea_by_id(cursor, tarea_id) is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        existentes = repository.count_adjuntos_by_tarea(cursor, tarea_id)
        disponibles = adjuntos_helpers.MAX_ADJUNTOS_POR_ENTIDAD - existentes
        contenidos = await adjuntos_helpers.leer_y_validar_adjuntos(files, maximo=max(disponibles, 0))

        nuevos_ids = []
        for filename, contenido, content_type in contenidos:
            ruta = save_attachment(tarea_id, filename, contenido, subdir="tareas")
            nuevos_ids.append(
                repository.insert_adjunto_tarea(cursor, tarea_id, filename, ruta, content_type, len(contenido))
            )
        db_conn.commit()

        filas = [fila for fila in repository.list_adjuntos_by_tarea(cursor, tarea_id) if fila["id"] in nuevos_ids]
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error agregando adjuntos a tarea %s", tarea_id)
        raise HTTPException(status_code=500, detail="No se pudieron agregar los adjuntos") from None
    finally:
        release_connection(db_conn)
    return [AdjuntoOut(**fila) for fila in filas]


@router.get("/tareas/{tarea_id}/adjuntos/{adjunto_id}/descargar")
def descargar_adjunto_tarea(
    tarea_id: int, adjunto_id: int, _: UsuarioActual = Depends(require_no_externo)
) -> FileResponse:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        adjunto = repository.get_adjunto_de_tarea(cursor, tarea_id, adjunto_id)
    finally:
        release_connection(db_conn)
    if adjunto is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado para esta tarea")
    if not os.path.isfile(adjunto["ruta_almacenamiento"]):
        logger.error(
            "Adjunto %s de tarea %s tiene fila en BD pero el archivo no existe en disco (%s)",
            adjunto_id,
            tarea_id,
            adjunto["ruta_almacenamiento"],
        )
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible en el servidor")

    return FileResponse(
        adjunto["ruta_almacenamiento"],
        media_type=adjunto["tipo_mime"] or "application/octet-stream",
        filename=adjunto["nombre_archivo"],
    )

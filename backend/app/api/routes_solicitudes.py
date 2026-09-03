from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import EmailStr

from app.api import adjuntos_helpers
from app.api.schemas import (
    AdjuntoOut,
    ChatSolicitudRequest,
    ChatSolicitudResponse,
    ClienteSugerido,
    ComentarioCreateUpdate,
    ComentarioOut,
    EnlaceTareaOut,
    HealthResponse,
    HitoOut,
    SolicitudDetalle,
    SolicitudResumen,
    SolicitudUpdate,
    SolicitudUpdateExterno,
    TareaCreateUpdate,
    TareaOut,
)
from app.auth.dependencies import (
    UsuarioActual,
    get_current_user,
    require_no_externo,
    require_scrum_master,
    require_scrum_master_o_responsable_solicitud,
)
from app.config import settings
from app.db import repository
from app.db.connection import get_connection, release_connection
from app.email_ingest.title_synthesizer import synthesize_title
from app.md_generator.template import render_solicitud_md
from app.models import NuevaSolicitud, ParsedEmail
from app.storage import save_attachment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Reexportados desde adjuntos_helpers (compartido con routes_tareas.py, Fase 1.21) para no
# romper el nombre que ya usan los tests (`routes.MAX_ADJUNTO_SIZE_BYTES`, etc.).
MAX_ADJUNTOS_POR_SOLICITUD = adjuntos_helpers.MAX_ADJUNTOS_POR_ENTIDAD
MAX_ADJUNTO_SIZE_BYTES = adjuntos_helpers.MAX_ADJUNTO_SIZE_BYTES
_leer_y_validar_adjuntos = adjuntos_helpers.leer_y_validar_adjuntos


def _crear_solicitud_con_adjuntos(
    cursor,
    solicitud: NuevaSolicitud,
    contenidos: list[tuple[str, bytes, str | None]],
    dedupe_seed: str,
    now: datetime,
    actor: str = "PUBLICO",
) -> int:
    id_solicitud = repository.insert_solicitud(cursor, solicitud, actor=actor)

    rutas_adjuntos = []
    for filename, contenido, content_type in contenidos:
        ruta = save_attachment(id_solicitud, filename, contenido)
        repository.insert_adjunto(cursor, id_solicitud, filename, ruta, content_type, len(contenido))
        rutas_adjuntos.append(ruta)

    # El generador de .md fue diseñado para el canal de correo; se le pasa un ParsedEmail
    # sintético (mismo contrato) para reutilizarlo sin duplicar lógica, sea cual sea el canal.
    parsed_email_equivalente = ParsedEmail(
        message_id=dedupe_seed,
        sender_email=solicitud.solicitante_email,
        subject=solicitud.titulo,
        body_text=solicitud.descripcion_original,
        body_html=None,
        received_at=now,
    )
    ruta_md = render_solicitud_md(id_solicitud, solicitud, parsed_email_equivalente, rutas_adjuntos)
    repository.insert_solicitud_md(cursor, id_solicitud, ruta_md)
    return id_solicitud


def _require_propia_si_externo(usuario_actual: UsuarioActual, solicitud: dict) -> None:
    """El rol EXTERNO solo puede ver/tocar sus propias solicitudes (donde es el solicitante).
    404 en vez de 403 para no confirmarle que un id ajeno existe."""
    if usuario_actual.codigo_rol_scrum == "EXTERNO" and solicitud.get("solicitante_id") != usuario_actual.id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/clientes", response_model=list[ClienteSugerido])
def buscar_clientes(q: str = Query(default="", max_length=200)) -> list[ClienteSugerido]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        nombres = repository.search_cliente_names(cursor, q)
    finally:
        release_connection(db_conn)
    return [ClienteSugerido(nombre=nombre) for nombre in nombres]


@router.get("/solicitudes", response_model=list[SolicitudResumen])
def listar_solicitudes(
    cliente: str = Query(default="", max_length=200),
    nombre: str = Query(default="", max_length=200),
    estatus: str = Query(default="", max_length=15),
    orden_por: str = Query(default="", max_length=20),
    involucrado_id: int | None = Query(default=None),
    usuario_actual: UsuarioActual = Depends(get_current_user),
) -> list[SolicitudResumen]:
    # El rol EXTERNO nunca puede ver solicitudes ajenas: se ignora cualquier involucrado_id que
    # mande el cliente y se fuerza el propio id, sin importar lo que venga en el query.
    if usuario_actual.codigo_rol_scrum == "EXTERNO":
        involucrado_id = usuario_actual.id

    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_solicitudes(
            cursor,
            cliente=cliente or None,
            nombre=nombre or None,
            estatus=estatus or None,
            orden_por=orden_por or None,
            involucrado_id=involucrado_id,
        )
    finally:
        release_connection(db_conn)
    return [SolicitudResumen(**fila) for fila in filas]


@router.post("/solicitudes/chat", response_model=ChatSolicitudResponse, status_code=201)
async def crear_solicitud_chat(
    solicitante_email: Annotated[EmailStr, Form()],
    titulo: Annotated[str, Form(min_length=1, max_length=500)],
    descripcion: Annotated[str, Form(min_length=1)],
    cliente: Annotated[str | None, Form(max_length=100)] = None,
    files: Annotated[list[UploadFile], File()] = [],
) -> ChatSolicitudResponse:
    body = ChatSolicitudRequest(
        solicitante_email=solicitante_email, titulo=titulo, descripcion=descripcion, cliente=cliente
    )
    contenidos = await _leer_y_validar_adjuntos(files)

    now = datetime.now(timezone.utc)
    dedupe_seed = f"chat:{body.solicitante_email}:{uuid.uuid4()}"

    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()

        cliente_resuelto = repository.get_or_create_cliente(cursor, body.cliente)

        solicitud = NuevaSolicitud(
            titulo=synthesize_title(body.titulo, dedupe_seed=dedupe_seed, received_at=now),
            descripcion=body.descripcion[:4000],
            descripcion_original=body.descripcion,
            solicitante_email=body.solicitante_email,
            cliente=cliente_resuelto,
            tipo=settings.tipo_nueva_solicitud,
            status_cd=settings.status_cd_nueva,
            canal_origen="CHAT",
        )

        id_solicitud = _crear_solicitud_con_adjuntos(cursor, solicitud, contenidos, dedupe_seed, now)

        db_conn.commit()
        logger.info(
            "Solicitud %s creada por chat (cliente=%s)",
            id_solicitud,
            cliente_resuelto or "SIN IDENTIFICAR",
        )
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando solicitud de chat")
        raise HTTPException(status_code=500, detail="No se pudo crear la solicitud") from None
    finally:
        release_connection(db_conn)

    return ChatSolicitudResponse(
        id_solicitud=id_solicitud,
        titulo=solicitud.titulo,
        cliente=cliente_resuelto,
        status_cd=solicitud.status_cd,
    )


@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudDetalle)
def obtener_solicitud(
    solicitud_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> SolicitudDetalle:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        fila = repository.get_solicitud_by_id(cursor, solicitud_id)
    finally:
        release_connection(db_conn)
    if fila is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _require_propia_si_externo(usuario_actual, fila)
    return SolicitudDetalle(**fila)


@router.put("/solicitudes/{solicitud_id}", response_model=SolicitudDetalle)
def actualizar_solicitud(
    solicitud_id: int, body: SolicitudUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> SolicitudDetalle:
    if usuario_actual.codigo_rol_scrum == "EXTERNO":
        raise HTTPException(status_code=403, detail="Usa PUT /solicitudes/{id}/mi-solicitud")

    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()

        solicitud_antes = repository.get_solicitud_by_id(cursor, solicitud_id)

        cliente_resuelto = repository.get_or_create_cliente(cursor, body.cliente)
        cliente_id = repository.find_cliente_id_by_name(cursor, cliente_resuelto) if cliente_resuelto else None
        tipo_id = repository.find_tipo_id(cursor, body.tipo)
        canal_id = repository.find_canal_id_by_name(cursor, body.canal)

        filas_afectadas = repository.update_solicitud(
            cursor,
            solicitud_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            cliente_id=cliente_id,
            tipo_id=tipo_id,
            canal_id=canal_id,
            codigo_estatus=body.codigo_estatus,
            orden_prioridad=body.orden_prioridad,
            fecha_completado=body.fecha_completado,
            fecha_entrega=body.fecha_entrega,
            responsable_atencion_id=body.responsable_atencion_id,
            actor=usuario_actual.usuario,
        )
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        responsable_atencion_anterior = (solicitud_antes or {}).get("responsable_atencion_id")
        if body.responsable_atencion_id and body.responsable_atencion_id != responsable_atencion_anterior:
            repository.insert_notificacion(
                cursor,
                body.responsable_atencion_id,
                tipo="SOLICITUD_ASIGNADA",
                mensaje=f"Se te asignó la atención de la solicitud '{body.nombre}'",
                entidad_tipo="SOLICITUD",
                entidad_id=solicitud_id,
            )

        fila = repository.get_solicitud_by_id(cursor, solicitud_id)
        db_conn.commit()
    except HTTPException:
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error actualizando solicitud %s", solicitud_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar la solicitud") from None
    finally:
        release_connection(db_conn)

    return SolicitudDetalle(**fila)


@router.put("/solicitudes/{solicitud_id}/mi-solicitud", response_model=SolicitudDetalle)
def actualizar_mi_solicitud(
    solicitud_id: int, body: SolicitudUpdateExterno, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> SolicitudDetalle:
    """Edición restringida para quien creó la solicitud (pensada para el rol EXTERNO, pero el
    chequeo es de dueño+estatus, no de rol): solo mientras sigue en "EN ESPERA"."""
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()

        solicitud_antes = repository.get_solicitud_by_id(cursor, solicitud_id)
        if solicitud_antes is None or solicitud_antes["solicitante_id"] != usuario_actual.id:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        if solicitud_antes["codigo_estatus"] != "EN ESPERA":
            raise HTTPException(
                status_code=409, detail="Solo se puede editar mientras la solicitud está En espera"
            )

        cliente_resuelto = repository.get_or_create_cliente(cursor, body.cliente)
        cliente_id = repository.find_cliente_id_by_name(cursor, cliente_resuelto) if cliente_resuelto else None
        tipo_id = repository.find_tipo_id(cursor, body.tipo)

        repository.update_solicitud_externo(
            cursor,
            solicitud_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            cliente_id=cliente_id,
            tipo_id=tipo_id,
            actor=usuario_actual.usuario,
        )
        fila = repository.get_solicitud_by_id(cursor, solicitud_id)
        db_conn.commit()
    except HTTPException:
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error actualizando (externo) solicitud %s", solicitud_id)
        raise HTTPException(status_code=500, detail="No se pudo actualizar la solicitud") from None
    finally:
        release_connection(db_conn)

    return SolicitudDetalle(**fila)


@router.delete("/solicitudes/{solicitud_id}", status_code=204)
def borrar_solicitud(solicitud_id: int, usuario_actual: UsuarioActual = Depends(require_scrum_master)) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.delete_solicitud(cursor, solicitud_id, actor=usuario_actual.usuario)
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        db_conn.commit()
    except HTTPException:
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error borrando solicitud %s", solicitud_id)
        raise HTTPException(status_code=500, detail="No se pudo borrar la solicitud") from None
    finally:
        release_connection(db_conn)


@router.get("/solicitudes/{solicitud_id}/tareas", response_model=list[TareaOut])
def listar_tareas(solicitud_id: int, _: UsuarioActual = Depends(require_no_externo)) -> list[TareaOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_tareas_by_solicitud(cursor, solicitud_id)
    finally:
        release_connection(db_conn)
    return [TareaOut(**fila) for fila in filas]


@router.get("/solicitudes/{solicitud_id}/comentarios", response_model=list[ComentarioOut])
def listar_comentarios_solicitud(
    solicitud_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> list[ComentarioOut]:
    """Agrega los comentarios de todas las tareas de la solicitud, para verlos de un
    vistazo desde el detalle de la solicitud (no solo entrando a cada tarea)."""
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        solicitud = repository.get_solicitud_by_id(cursor, solicitud_id)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        _require_propia_si_externo(usuario_actual, solicitud)
        filas = repository.list_comentarios_by_solicitud(cursor, solicitud_id)
    finally:
        release_connection(db_conn)
    return [ComentarioOut(**fila) for fila in filas]


@router.post("/solicitudes/{solicitud_id}/comentarios", response_model=ComentarioOut, status_code=201)
def crear_comentario_solicitud(
    solicitud_id: int, body: ComentarioCreateUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> ComentarioOut:
    """Comentario a nivel solicitud (no ligado a ninguna tarea) — pensado para el rol EXTERNO,
    pero cualquier rol interno puede comentar cualquier solicitud, igual que ya pueden comentar
    cualquier tarea. Ya aparece en `listar_comentarios_solicitud` sin cambios ahí."""
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        solicitud = repository.get_solicitud_by_id(cursor, solicitud_id)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        _require_propia_si_externo(usuario_actual, solicitud)

        comentario_id = repository.insert_comentario(
            cursor,
            solicitud_id=solicitud_id,
            tarea_id=None,
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
        logger.exception("Error creando comentario para solicitud %s", solicitud_id)
        raise HTTPException(status_code=500, detail="No se pudo crear el comentario") from None
    finally:
        release_connection(db_conn)

    return ComentarioOut(**fila)


@router.get("/solicitudes/{solicitud_id}/hitos", response_model=list[HitoOut])
def listar_hitos_solicitud(solicitud_id: int, _: UsuarioActual = Depends(require_no_externo)) -> list[HitoOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_hitos_by_solicitud(cursor, solicitud_id)
    finally:
        release_connection(db_conn)
    return [HitoOut(**fila) for fila in filas]


@router.get("/solicitudes/{solicitud_id}/enlaces", response_model=list[EnlaceTareaOut])
def listar_enlaces_solicitud(
    solicitud_id: int, _: UsuarioActual = Depends(require_no_externo)
) -> list[EnlaceTareaOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_enlaces_by_solicitud(cursor, solicitud_id)
    finally:
        release_connection(db_conn)
    return [EnlaceTareaOut(**fila) for fila in filas]


@router.get("/solicitudes/{solicitud_id}/adjuntos", response_model=list[AdjuntoOut])
def listar_adjuntos_solicitud(
    solicitud_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> list[AdjuntoOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        solicitud = repository.get_solicitud_by_id(cursor, solicitud_id)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        _require_propia_si_externo(usuario_actual, solicitud)
        filas = repository.list_adjuntos_by_solicitud(cursor, solicitud_id)
    finally:
        release_connection(db_conn)
    return [AdjuntoOut(**fila) for fila in filas]


@router.post("/solicitudes/{solicitud_id}/adjuntos", response_model=list[AdjuntoOut], status_code=201)
async def agregar_adjuntos_solicitud(
    solicitud_id: int,
    files: Annotated[list[UploadFile], File()] = [],
    usuario_actual: UsuarioActual = Depends(get_current_user),
) -> list[AdjuntoOut]:
    """Fase 1.21: agrega adjuntos a una solicitud ya creada (antes solo se podían adjuntar al
    crearla). Valida que el total existentes + nuevos no pase de 5, igual que al crear."""
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        solicitud = repository.get_solicitud_by_id(cursor, solicitud_id)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        _require_propia_si_externo(usuario_actual, solicitud)

        existentes = repository.count_adjuntos_by_solicitud(cursor, solicitud_id)
        disponibles = adjuntos_helpers.MAX_ADJUNTOS_POR_ENTIDAD - existentes
        contenidos = await adjuntos_helpers.leer_y_validar_adjuntos(files, maximo=max(disponibles, 0))

        nuevos_ids = []
        for filename, contenido, content_type in contenidos:
            ruta = save_attachment(solicitud_id, filename, contenido)
            nuevos_ids.append(
                repository.insert_adjunto(cursor, solicitud_id, filename, ruta, content_type, len(contenido))
            )
        db_conn.commit()

        filas = [
            fila
            for fila in repository.list_adjuntos_by_solicitud(cursor, solicitud_id)
            if fila["id"] in nuevos_ids
        ]
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error agregando adjuntos a solicitud %s", solicitud_id)
        raise HTTPException(status_code=500, detail="No se pudieron agregar los adjuntos") from None
    finally:
        release_connection(db_conn)
    return [AdjuntoOut(**fila) for fila in filas]


@router.get("/solicitudes/{solicitud_id}/adjuntos/{adjunto_id}/descargar")
def descargar_adjunto_solicitud(
    solicitud_id: int, adjunto_id: int, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> FileResponse:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        solicitud = repository.get_solicitud_by_id(cursor, solicitud_id)
        if solicitud is not None:
            _require_propia_si_externo(usuario_actual, solicitud)
        adjunto = repository.get_adjunto_de_solicitud(cursor, solicitud_id, adjunto_id)
    finally:
        release_connection(db_conn)
    if adjunto is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado para esta solicitud")
    if not os.path.isfile(adjunto["ruta_almacenamiento"]):
        logger.error(
            "Adjunto %s de solicitud %s tiene fila en BD pero el archivo no existe en disco (%s)",
            adjunto_id,
            solicitud_id,
            adjunto["ruta_almacenamiento"],
        )
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible en el servidor")

    return FileResponse(
        adjunto["ruta_almacenamiento"],
        media_type=adjunto["tipo_mime"] or "application/octet-stream",
        filename=adjunto["nombre_archivo"],
    )


@router.post("/solicitudes/{solicitud_id}/tareas", response_model=TareaOut, status_code=201)
def crear_tarea(
    solicitud_id: int, body: TareaCreateUpdate, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> TareaOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        solicitud = repository.get_solicitud_by_id(cursor, solicitud_id)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        require_scrum_master_o_responsable_solicitud(
            usuario_actual, solicitud.get("responsable_atencion_id")
        )

        tarea_id = repository.insert_tarea(
            cursor,
            solicitud_id,
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
        if body.responsable_id:
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
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando tarea para solicitud %s", solicitud_id)
        raise HTTPException(status_code=500, detail="No se pudo crear la tarea") from None
    finally:
        release_connection(db_conn)

    return TareaOut(**fila)


@router.post("/solicitudes/formulario", response_model=ChatSolicitudResponse, status_code=201)
async def crear_solicitud_formulario(
    solicitante_email: Annotated[EmailStr, Form()],
    titulo: Annotated[str, Form(min_length=1, max_length=500)],
    descripcion: Annotated[str, Form(min_length=1)],
    tipo: Annotated[str, Form(min_length=1, max_length=100)],
    canal: Annotated[str, Form(min_length=1, max_length=100)],
    cliente: Annotated[str | None, Form(max_length=100)] = None,
    orden_prioridad: Annotated[int, Form(ge=1, le=5)] = 3,
    files: Annotated[list[UploadFile], File()] = [],
    usuario_actual: UsuarioActual = Depends(get_current_user),
) -> ChatSolicitudResponse:
    """Fase 1.6 — página de Solicitudes: formulario tradicional (un solo paso), con
    solicitante y tipo elegidos de catálogo en vez de resueltos/asumidos como en chat/correo.
    A diferencia de chat/correo, aquí el canal también lo elige el usuario (por defecto
    "Formulario" en el frontend, pero editable) en vez de asumirse fijo por el origen."""
    contenidos = await _leer_y_validar_adjuntos(files)

    now = datetime.now(timezone.utc)
    dedupe_seed = f"formulario:{solicitante_email}:{uuid.uuid4()}"

    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()

        cliente_resuelto = repository.get_or_create_cliente(cursor, cliente)

        solicitud = NuevaSolicitud(
            titulo=synthesize_title(titulo, dedupe_seed=dedupe_seed, received_at=now),
            descripcion=descripcion[:4000],
            descripcion_original=descripcion,
            solicitante_email=solicitante_email,
            cliente=cliente_resuelto,
            tipo=tipo,
            status_cd=settings.status_cd_nueva,
            canal_origen="FORMULARIO",
            canal_nombre=canal,
            orden_prioridad=orden_prioridad,
        )

        id_solicitud = _crear_solicitud_con_adjuntos(
            cursor, solicitud, contenidos, dedupe_seed, now, actor=usuario_actual.usuario
        )

        db_conn.commit()
        logger.info(
            "Solicitud %s creada por formulario (cliente=%s)",
            id_solicitud,
            cliente_resuelto or "SIN IDENTIFICAR",
        )
    except Exception:
        db_conn.rollback()
        logger.exception("Error creando solicitud de formulario")
        raise HTTPException(status_code=500, detail="No se pudo crear la solicitud") from None
    finally:
        release_connection(db_conn)

    return ChatSolicitudResponse(
        id_solicitud=id_solicitud,
        titulo=solicitud.titulo,
        cliente=cliente_resuelto,
        status_cd=solicitud.status_cd,
    )

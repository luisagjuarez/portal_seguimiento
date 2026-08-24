from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import EmailStr

from app.api.schemas import (
    ChatSolicitudRequest,
    ChatSolicitudResponse,
    ClienteSugerido,
    HealthResponse,
    SolicitudDetalle,
    SolicitudResumen,
    SolicitudUpdate,
    TareaCreateUpdate,
    TareaOut,
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

# Límite de producto para los canales expuestos en un navegador (chat y formulario), sin
# autenticación fuerte: el canal de correo no tiene este límite porque ya está acotado a
# quien tenga acceso al buzón de solicitudes.
MAX_ADJUNTOS_POR_SOLICITUD = 5
MAX_ADJUNTO_SIZE_BYTES = 10 * 1024 * 1024


async def _leer_y_validar_adjuntos(files: list[UploadFile]) -> list[tuple[str, bytes, str | None]]:
    if len(files) > MAX_ADJUNTOS_POR_SOLICITUD:
        raise HTTPException(
            status_code=422, detail=f"Máximo {MAX_ADJUNTOS_POR_SOLICITUD} adjuntos por solicitud"
        )

    contenidos: list[tuple[str, bytes, str | None]] = []
    for file in files:
        contenido = await file.read()
        if len(contenido) > MAX_ADJUNTO_SIZE_BYTES:
            raise HTTPException(
                status_code=422,
                detail=f"El archivo '{file.filename}' supera el límite de "
                f"{MAX_ADJUNTO_SIZE_BYTES // (1024 * 1024)} MB",
            )
        contenidos.append((file.filename, contenido, file.content_type))
    return contenidos


def _crear_solicitud_con_adjuntos(
    cursor,
    solicitud: NuevaSolicitud,
    contenidos: list[tuple[str, bytes, str | None]],
    dedupe_seed: str,
    now: datetime,
) -> int:
    id_solicitud = repository.insert_solicitud(cursor, solicitud)

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
) -> list[SolicitudResumen]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_solicitudes(
            cursor, cliente=cliente or None, nombre=nombre or None, estatus=estatus or None
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
def obtener_solicitud(solicitud_id: int) -> SolicitudDetalle:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        fila = repository.get_solicitud_by_id(cursor, solicitud_id)
    finally:
        release_connection(db_conn)
    if fila is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return SolicitudDetalle(**fila)


@router.put("/solicitudes/{solicitud_id}", response_model=SolicitudDetalle)
def actualizar_solicitud(solicitud_id: int, body: SolicitudUpdate) -> SolicitudDetalle:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()

        cliente_resuelto = repository.get_or_create_cliente(cursor, body.cliente)
        cliente_id = repository.find_cliente_id_by_name(cursor, cliente_resuelto) if cliente_resuelto else None
        tipo_id = repository.find_tipo_id(cursor, body.tipo)

        filas_afectadas = repository.update_solicitud(
            cursor,
            solicitud_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            cliente_id=cliente_id,
            tipo_id=tipo_id,
            codigo_estatus=body.codigo_estatus,
        )
        if filas_afectadas == 0:
            db_conn.rollback()
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

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


@router.delete("/solicitudes/{solicitud_id}", status_code=204)
def borrar_solicitud(solicitud_id: int) -> None:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas_afectadas = repository.delete_solicitud(cursor, solicitud_id)
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
def listar_tareas(solicitud_id: int) -> list[TareaOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        filas = repository.list_tareas_by_solicitud(cursor, solicitud_id)
    finally:
        release_connection(db_conn)
    return [TareaOut(**fila) for fila in filas]


@router.post("/solicitudes/{solicitud_id}/tareas", response_model=TareaOut, status_code=201)
def crear_tarea(solicitud_id: int, body: TareaCreateUpdate) -> TareaOut:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        tarea_id = repository.insert_tarea(
            cursor,
            solicitud_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            responsable_id=body.responsable_id,
            esta_completa=body.esta_completa,
        )
        fila = repository.get_tarea_by_id(cursor, tarea_id)
        db_conn.commit()
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
    cliente: Annotated[str | None, Form(max_length=100)] = None,
    files: Annotated[list[UploadFile], File()] = [],
) -> ChatSolicitudResponse:
    """Fase 1.6 — página de Solicitudes: formulario tradicional (un solo paso), con
    solicitante y tipo elegidos de catálogo en vez de resueltos/asumidos como en chat/correo."""
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
        )

        id_solicitud = _crear_solicitud_con_adjuntos(cursor, solicitud, contenidos, dedupe_seed, now)

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

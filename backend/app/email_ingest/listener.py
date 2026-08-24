from __future__ import annotations

import imaplib
import logging
import time

from app.config import settings
from app.db import repository
from app.db.connection import get_connection, release_connection
from app.email_ingest.client_matcher import detect_cliente
from app.email_ingest.parser import parse_email, truncate_description
from app.email_ingest.title_synthesizer import synthesize_title
from app.md_generator.template import render_solicitud_md
from app.models import NuevaSolicitud
from app.storage import save_attachment

logger = logging.getLogger(__name__)


def _connect_imap() -> imaplib.IMAP4:
    if settings.imap_use_ssl:
        conn: imaplib.IMAP4 = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    else:
        conn = imaplib.IMAP4(settings.imap_host, settings.imap_port)
    conn.login(settings.imap_user, settings.imap_password)
    conn.select(settings.imap_mailbox)
    return conn


def _search_candidate_uids(conn: imaplib.IMAP4) -> list[bytes]:
    # El criterio SUBJECT de IMAP SEARCH ya hace la coincidencia de substring
    # case-insensitive en el servidor, así que el filtro de asunto no requiere
    # descargar cada correo completo para revisarlo en el cliente.
    status, data = conn.search(None, "UNSEEN", "SUBJECT", f'"{settings.subject_filter}"')
    if status != "OK" or not data or data[0] is None:
        return []
    return data[0].split()


def _fetch_raw_message(conn: imaplib.IMAP4, uid: bytes) -> bytes:
    status, data = conn.fetch(uid, "(RFC822)")
    if status != "OK" or not data or data[0] is None:
        raise RuntimeError(f"No se pudo leer el mensaje uid={uid!r}")
    return data[0][1]


def _mark_seen(conn: imaplib.IMAP4, uid: bytes) -> None:
    conn.store(uid, "+FLAGS", "\\Seen")
    if settings.imap_processed_folder:
        conn.copy(uid, settings.imap_processed_folder)
        conn.store(uid, "+FLAGS", "\\Deleted")
        conn.expunge()


def process_message(conn: imaplib.IMAP4, uid: bytes) -> None:
    raw = _fetch_raw_message(conn, uid)
    parsed = parse_email(raw)

    if not parsed.message_id:
        logger.warning("Correo uid=%s sin Message-ID: se procesa sin protección de dedup", uid)

    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()

        if parsed.message_id and repository.is_message_processed(cursor, parsed.message_id):
            logger.info("Correo %s ya fue procesado antes, se omite", parsed.message_id)
            _mark_seen(conn, uid)
            return

        catalog_names = repository.list_cliente_names(cursor)
        cliente_candidato = detect_cliente(parsed.body_text, catalog_names)
        cliente_resuelto = repository.get_or_create_cliente(cursor, cliente_candidato)

        solicitud = NuevaSolicitud(
            titulo=synthesize_title(
                parsed.subject, dedupe_seed=parsed.message_id, received_at=parsed.received_at
            ),
            descripcion=truncate_description(parsed.body_text),
            descripcion_original=parsed.body_text,
            solicitante_email=parsed.sender_email,
            cliente=cliente_resuelto,
            tipo=settings.tipo_nueva_solicitud,
            status_cd=settings.status_cd_nueva,
            canal_origen="EMAIL",
        )

        # Todo lo que sigue va en una sola transacción: si algo falla, se hace rollback
        # completo en vez de dejar una solicitud a medio registrar.
        id_solicitud = repository.insert_solicitud(cursor, solicitud)

        rutas_adjuntos = []
        for adjunto in parsed.attachments:
            ruta = save_attachment(id_solicitud, adjunto.filename, adjunto.content)
            repository.insert_adjunto(
                cursor,
                id_solicitud,
                adjunto.filename,
                ruta,
                adjunto.content_type,
                len(adjunto.content),
            )
            rutas_adjuntos.append(ruta)

        ruta_md = render_solicitud_md(id_solicitud, solicitud, parsed, rutas_adjuntos)
        repository.insert_solicitud_md(cursor, id_solicitud, ruta_md)

        if parsed.message_id:
            repository.mark_email_processed(cursor, parsed.message_id, id_solicitud)

        db_conn.commit()
        logger.info(
            "Solicitud %s creada (cliente=%s) a partir del correo %s",
            id_solicitud,
            cliente_resuelto or "SIN IDENTIFICAR",
            parsed.message_id,
        )
    except Exception:
        db_conn.rollback()
        raise
    finally:
        release_connection(db_conn)

    _mark_seen(conn, uid)


def run_forever() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info(
        "Worker de ingestión de correo iniciado (mailbox=%s, filtro='%s', intervalo=%ss)",
        settings.imap_mailbox,
        settings.subject_filter,
        settings.poll_interval_seconds,
    )
    while True:
        try:
            conn = _connect_imap()
            try:
                for uid in _search_candidate_uids(conn):
                    try:
                        process_message(conn, uid)
                    except Exception:
                        logger.exception("Error procesando el correo uid=%s", uid)
            finally:
                conn.logout()
        except Exception:
            logger.exception("Error en el ciclo de polling IMAP")

        time.sleep(settings.poll_interval_seconds)

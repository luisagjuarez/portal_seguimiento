from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


@dataclass(frozen=True)
class Settings:
    # Conexión IMAP
    imap_host: str = os.environ.get("IMAP_HOST", "localhost")
    imap_port: int = _get_int("IMAP_PORT", 993)
    imap_user: str = os.environ.get("IMAP_USER", "")
    imap_password: str = os.environ.get("IMAP_PASSWORD", "")
    imap_mailbox: str = os.environ.get("IMAP_MAILBOX", "INBOX")
    imap_use_ssl: bool = _get_bool("IMAP_USE_SSL", True)
    imap_processed_folder: str = os.environ.get("IMAP_PROCESSED_FOLDER", "")

    # Filtro y polling
    subject_filter: str = os.environ.get("SUBJECT_FILTER", "Nueva solicitud")
    poll_interval_seconds: int = _get_int("POLL_INTERVAL_SECONDS", 60)

    # PostgreSQL
    postgres_host: str = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port: int = _get_int("POSTGRES_PORT", 5432)
    postgres_user: str = os.environ.get("POSTGRES_USER", "")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "")
    postgres_db: str = os.environ.get("POSTGRES_DB", "dovela_control")
    postgres_schema: str = os.environ.get("POSTGRES_SCHEMA", "solicitudes")

    # Almacenamiento (simula NFS)
    attachments_dir: str = os.environ.get("ATTACHMENTS_DIR", "./data/nfs/adjuntos")
    md_dir: str = os.environ.get("MD_DIR", "./data/nfs/archivos_md")

    # Valores por defecto de negocio (Módulo 1.1)
    status_cd_nueva: str = os.environ.get("STATUS_CD_NUEVA", "EN ESPERA")
    tipo_nueva_solicitud: str = os.environ.get("TIPO_NUEVA_SOLICITUD", "Nuevo")

    # API HTTP (Fase 1.2 — chat web)
    frontend_origin: str = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")


settings = Settings()

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
    # Subpath fijo bajo el que se sirve el portal (Fase 1.14) — separado de frontend_origin
    # porque ese es el origen puro que usa CORS, que por spec no puede llevar path.
    frontend_base_path: str = os.environ.get("FRONTEND_BASE_PATH", "/dovela_control")

    # Autenticación (login usuario/contraseña + JWT)
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY", "")
    jwt_expire_minutes: int = _get_int("JWT_EXPIRE_MINUTES", 480)

    # Envío de correo saliente (recuperación de contraseña)
    smtp_host: str = os.environ.get("SMTP_HOST", "localhost")
    smtp_port: int = _get_int("SMTP_PORT", 25)
    smtp_user: str = os.environ.get("SMTP_USER", "")
    smtp_password: str = os.environ.get("SMTP_PASSWORD", "")
    smtp_use_tls: bool = _get_bool("SMTP_USE_TLS", False)
    smtp_from: str = os.environ.get("SMTP_FROM", "no-responder@dovela.com")
    reset_token_expire_minutes: int = _get_int("RESET_TOKEN_EXPIRE_MINUTES", 30)


settings = Settings()

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedAttachment:
    filename: str
    content: bytes
    content_type: str | None = None


@dataclass
class ParsedEmail:
    message_id: str
    sender_email: str
    subject: str
    body_text: str
    body_html: str | None
    received_at: datetime
    attachments: list[ParsedAttachment] = field(default_factory=list)


@dataclass
class NuevaSolicitud:
    """Datos listos para insertarse en EBA_DEMO_MD_PROJECTS (tabla ya existente)."""

    titulo: str
    descripcion: str
    descripcion_original: str
    solicitante_email: str
    cliente: str | None
    tipo: str
    status_cd: str
    canal_origen: str = "EMAIL"
    orden_prioridad: int = 3
    # Nombre de canal elegido explícitamente por el usuario (formulario de Solicitudes);
    # si viene, tiene prioridad sobre canal_origen al resolver el FK en insert_solicitud.
    canal_nombre: str | None = None

from __future__ import annotations

import hashlib
import re
from datetime import datetime

# EBA_DEMO_MD_PROJECTS.NAME es VARCHAR2(255) UNIQUE. Se le agrega siempre un folio corto
# para que dos solicitudes nunca choquen, sin depender de reintentos ni de consultar
# primero si el título ya existe.
MAX_NAME_LENGTH = 255
FOLIO_SEPARATOR = " - "

_NUEVA_SOLICITUD_PATTERN = re.compile(r"(?i)nueva\s+solicitud")
_LEADING_SEPARATORS_PATTERN = re.compile(r"^[\s:\-]+")


def _short_hash(seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return digest[:6].upper()


def synthesize_title(subject: str, dedupe_seed: str, received_at: datetime) -> str:
    """`dedupe_seed` es cualquier cadena que identifique unívocamente el origen del
    título (Message-ID del correo, o una semilla propia de otros canales como el chat),
    para que el folio anexado nunca choque contra el UNIQUE de NAME."""
    base = _NUEVA_SOLICITUD_PATTERN.sub("", subject or "")
    base = _LEADING_SEPARATORS_PATTERN.sub("", base).strip()
    if not base:
        base = "Solicitud sin asunto"

    folio = f"{received_at:%Y%m%d}-{_short_hash(dedupe_seed or subject or base)}"
    suffix = f"{FOLIO_SEPARATOR}{folio}"

    max_base_length = MAX_NAME_LENGTH - len(suffix)
    if len(base) > max_base_length:
        base = base[: max_base_length - 1].rstrip() + "…"

    return f"{base}{suffix}"

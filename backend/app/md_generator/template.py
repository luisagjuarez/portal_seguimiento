from __future__ import annotations

import os
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.models import NuevaSolicitud, ParsedEmail

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_solicitud_md(
    id_solicitud: int,
    solicitud: NuevaSolicitud,
    parsed_email: ParsedEmail,
    rutas_adjuntos: list[str],
) -> str:
    template = _env.get_template("solicitud_template.md.j2")
    contenido = template.render(
        id_solicitud=id_solicitud,
        solicitud=solicitud,
        parsed_email=parsed_email,
        rutas_adjuntos=rutas_adjuntos,
        generado_en=datetime.now(timezone.utc),
    )

    os.makedirs(settings.md_dir, exist_ok=True)
    ruta = os.path.join(settings.md_dir, f"{id_solicitud}.md")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(contenido)
    return ruta

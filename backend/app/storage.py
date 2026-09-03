from __future__ import annotations

import os

from app.config import settings


def save_attachment(id_entidad: int, filename: str, content: bytes, subdir: str = "") -> str:
    """`subdir` separa el espacio de ids de tareas del de solicitudes (Fase 1.21): ambas
    tablas tienen su propia secuencia IDENTITY y sus ids pueden coincidir (p. ej. solicitud 73
    y tarea 73 al mismo tiempo), así que los adjuntos de tarea van bajo `adjuntos/tareas/<id>/`
    en vez de `adjuntos/<id>/` para no pisar archivos. Los de solicitud no cambian de ruta
    (subdir="" por default) para no romper compatibilidad con lo ya guardado."""
    directory = os.path.join(settings.attachments_dir, subdir, str(id_entidad))
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "wb") as fh:
        fh.write(content)
    return path

from __future__ import annotations

import os

from app.config import settings


def save_attachment(id_solicitud: int, filename: str, content: bytes) -> str:
    directory = os.path.join(settings.attachments_dir, str(id_solicitud))
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "wb") as fh:
        fh.write(content)
    return path

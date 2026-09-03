from __future__ import annotations

from fastapi import HTTPException, UploadFile

# Límite de producto para los canales expuestos en un navegador (solicitudes y tareas), sin
# autenticación fuerte en el caso de chat/formulario: el canal de correo no tiene este límite
# porque ya está acotado a quien tenga acceso al buzón. Compartido entre routes_solicitudes.py
# y routes_tareas.py (Fase 1.21).
MAX_ADJUNTOS_POR_ENTIDAD = 5
MAX_ADJUNTO_SIZE_BYTES = 10 * 1024 * 1024


async def leer_y_validar_adjuntos(
    files: list[UploadFile], maximo: int = MAX_ADJUNTOS_POR_ENTIDAD
) -> list[tuple[str, bytes, str | None]]:
    if len(files) > maximo:
        raise HTTPException(status_code=422, detail=f"Máximo {maximo} adjuntos")

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

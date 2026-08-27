from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

from app.auth.security import decode_access_token
from app.db import repository
from app.db.connection import get_connection, release_connection


@dataclass(frozen=True)
class UsuarioActual:
    id: int
    usuario: str
    nombre_completo: str
    codigo_rol_scrum: str | None
    correo_electronico: str | None
    debe_cambiar_password: bool


def get_current_user(authorization: str | None = Header(default=None)) -> UsuarioActual:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")

    payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    if payload is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        miembro = repository.get_miembro_by_id(cursor, int(payload["sub"]))
    finally:
        release_connection(db_conn)

    # No se confía solo en el JWT: si el Scrum Master desactivó el acceso o cambió el rol
    # después de emitido el token, el cambio debe surtir efecto de inmediato.
    if miembro is None or not miembro["acceso_activo"]:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

    return UsuarioActual(
        id=miembro["id"],
        usuario=miembro["usuario"],
        nombre_completo=miembro["nombre_completo"],
        codigo_rol_scrum=miembro["codigo_rol_scrum"],
        correo_electronico=miembro["correo_electronico"],
        debe_cambiar_password=miembro["debe_cambiar_password"],
    )


def require_scrum_master(usuario_actual: UsuarioActual = Depends(get_current_user)) -> UsuarioActual:
    if usuario_actual.codigo_rol_scrum != "SCRUM MASTER":
        raise HTTPException(status_code=403, detail="Solo el Scrum Master puede hacer esto")
    return usuario_actual


def require_scrum_master_or_product_owner(
    usuario_actual: UsuarioActual = Depends(get_current_user),
) -> UsuarioActual:
    if usuario_actual.codigo_rol_scrum not in {"SCRUM MASTER", "PRODUCT OWNER"}:
        raise HTTPException(
            status_code=403, detail="Solo el Scrum Master o el Product Owner pueden ver esto"
        )
    return usuario_actual


def require_autor_o_scrum_master(usuario_actual: UsuarioActual, creado_por: str) -> None:
    """A diferencia de las dependencias de arriba, esta no puede ser un `Depends` de FastAPI:
    el `creado_por` a comparar solo se conoce después de leer el registro de la BD dentro del
    propio endpoint."""
    if usuario_actual.usuario != creado_por and usuario_actual.codigo_rol_scrum != "SCRUM MASTER":
        raise HTTPException(status_code=403, detail="Solo el autor o el Scrum Master pueden hacer esto")

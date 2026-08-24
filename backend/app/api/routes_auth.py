from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import LoginRequest, LoginResponse, UsuarioActualOut
from app.auth.dependencies import UsuarioActual, get_current_user
from app.auth.security import create_access_token, verify_password
from app.db import repository
from app.db.connection import get_connection, release_connection

router = APIRouter(prefix="/api/auth")

_CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos"


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        miembro = repository.get_miembro_by_usuario(cursor, body.usuario)
    finally:
        release_connection(db_conn)

    # Mismo mensaje genérico si el usuario no existe, no tiene acceso activo, o la
    # contraseña es incorrecta — no se revela cuál de los tres pasó.
    if miembro is None or not miembro["acceso_activo"] or not miembro["password_hash"]:
        raise HTTPException(status_code=401, detail=_CREDENCIALES_INVALIDAS)
    if not verify_password(body.password, miembro["password_hash"]):
        raise HTTPException(status_code=401, detail=_CREDENCIALES_INVALIDAS)

    token = create_access_token(
        miembro["id"], miembro["usuario"], miembro["nombre_completo"], miembro["codigo_rol_scrum"]
    )
    return LoginResponse(
        access_token=token,
        usuario_actual=UsuarioActualOut(
            id=miembro["id"],
            usuario=miembro["usuario"],
            nombre_completo=miembro["nombre_completo"],
            codigo_rol_scrum=miembro["codigo_rol_scrum"],
        ),
    )


@router.get("/me", response_model=UsuarioActualOut)
def me(usuario_actual: UsuarioActual = Depends(get_current_user)) -> UsuarioActualOut:
    return UsuarioActualOut(
        id=usuario_actual.id,
        usuario=usuario_actual.usuario,
        nombre_completo=usuario_actual.nombre_completo,
        codigo_rol_scrum=usuario_actual.codigo_rol_scrum,
    )

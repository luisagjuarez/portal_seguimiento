from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    UsuarioActualOut,
)
from app.auth.dependencies import UsuarioActual, get_current_user
from app.auth.security import (
    create_access_token,
    generar_token_reset,
    hash_password,
    hash_token,
    verify_password,
)
from app.config import settings
from app.db import repository
from app.db.connection import get_connection, release_connection
from app.email_send.mailer import enviar_correo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth")

_CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos"
_MENSAJE_FORGOT_PASSWORD = "Si el correo está registrado, se envió un enlace de recuperación."


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
            correo_electronico=miembro["correo_electronico"],
            debe_cambiar_password=miembro["debe_cambiar_password"],
        ),
    )


@router.get("/me", response_model=UsuarioActualOut)
def me(usuario_actual: UsuarioActual = Depends(get_current_user)) -> UsuarioActualOut:
    return UsuarioActualOut(
        id=usuario_actual.id,
        usuario=usuario_actual.usuario,
        nombre_completo=usuario_actual.nombre_completo,
        codigo_rol_scrum=usuario_actual.codigo_rol_scrum,
        correo_electronico=usuario_actual.correo_electronico,
        debe_cambiar_password=usuario_actual.debe_cambiar_password,
    )


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest) -> dict:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        miembro = repository.get_miembro_by_email(cursor, body.correo_electronico)
        if miembro is not None and miembro["acceso_activo"]:
            token = generar_token_reset()
            expira_en = datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_expire_minutes)
            repository.crear_token_reset(cursor, miembro["id"], hash_token(token), expira_en)
            db_conn.commit()

            enlace = f"{settings.frontend_origin}/?reset_token={token}"
            cuerpo = (
                f"Hola {miembro['nombre_completo']},\n\n"
                "Recibimos una solicitud para restablecer tu contraseña del Portal de "
                f"Seguimiento DOVELA. Entra al siguiente enlace para elegir una nueva "
                f"(vence en {settings.reset_token_expire_minutes} minutos):\n\n{enlace}\n\n"
                "Si no fuiste tú quien lo solicitó, puedes ignorar este correo."
            )
            try:
                enviar_correo(miembro["correo_electronico"], "Recuperación de contraseña — Portal DOVELA", cuerpo)
            except Exception:
                logger.exception("No se pudo enviar el correo de recuperación al miembro %s", miembro["id"])
    except Exception:
        db_conn.rollback()
        logger.exception("Error generando el token de recuperación de contraseña")
    finally:
        release_connection(db_conn)

    # Mismo mensaje exista o no la cuenta (o incluso si algo falló internamente), para no
    # revelar qué correos están registrados.
    return {"detail": _MENSAJE_FORGOT_PASSWORD}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest) -> dict:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        registro = repository.get_token_reset(cursor, hash_token(body.token))
        ahora = datetime.now(timezone.utc)
        if registro is None or registro["usado_en"] is not None or registro["expira_en"] < ahora:
            raise HTTPException(status_code=400, detail="El enlace de recuperación no es válido o ya expiró")

        repository.set_password_miembro(cursor, registro["miembro_id"], hash_password(body.password_nueva))
        repository.marcar_token_usado(cursor, registro["id"])
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error restableciendo contraseña por token")
        raise HTTPException(status_code=500, detail="No se pudo restablecer la contraseña") from None
    finally:
        release_connection(db_conn)

    return {"detail": "Contraseña actualizada correctamente"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest, usuario_actual: UsuarioActual = Depends(get_current_user)
) -> dict:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        miembro = repository.get_miembro_by_id(cursor, usuario_actual.id)
        if miembro is None or not verify_password(body.password_actual, miembro["password_hash"] or ""):
            # 400 y no 401: un 401 dispara el logout automático del frontend (sesión
            # expirada), lo cual sería incorrecto para un simple typo de contraseña actual.
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")

        repository.set_password_miembro(cursor, usuario_actual.id, hash_password(body.password_nueva))
        db_conn.commit()
    except HTTPException:
        db_conn.rollback()
        raise
    except Exception:
        db_conn.rollback()
        logger.exception("Error cambiando contraseña del usuario %s", usuario_actual.id)
        raise HTTPException(status_code=500, detail="No se pudo cambiar la contraseña") from None
    finally:
        release_connection(db_conn)

    return {"detail": "Contraseña actualizada correctamente"}

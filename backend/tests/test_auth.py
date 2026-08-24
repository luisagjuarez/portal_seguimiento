from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.api.app import app
from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
import app.api.routes_auth as routes

client = TestClient(app)


class _FakeCursor:
    pass


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def _fake_miembro(**overrides):
    base = {
        "id": 1,
        "usuario": "DOVELA_LG",
        "nombre_completo": "Luis Gómez",
        "password_hash": hash_password("clave-secreta-1"),
        "codigo_rol_scrum": "SCRUM MASTER",
        "acceso_activo": True,
        "correo_electronico": "luis.gomez@dovela.com",
        "debe_cambiar_password": False,
    }
    base.update(overrides)
    return base


def test_hash_password_no_guarda_texto_plano():
    hashed = hash_password("clave-secreta-1")
    assert hashed != "clave-secreta-1"
    assert verify_password("clave-secreta-1", hashed) is True
    assert verify_password("otra-clave", hashed) is False


def test_login_success(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_usuario", lambda cursor, usuario: _fake_miembro())

    response = client.post("/api/auth/login", json={"usuario": "DOVELA_LG", "password": "clave-secreta-1"})

    assert response.status_code == 200
    body = response.json()
    assert body["usuario_actual"]["usuario"] == "DOVELA_LG"
    assert body["usuario_actual"]["codigo_rol_scrum"] == "SCRUM MASTER"
    assert "access_token" in body


def test_login_contrasena_incorrecta(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_usuario", lambda cursor, usuario: _fake_miembro())

    response = client.post("/api/auth/login", json={"usuario": "DOVELA_LG", "password": "incorrecta"})

    assert response.status_code == 401


def test_login_usuario_no_existe(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_usuario", lambda cursor, usuario: None)

    response = client.post("/api/auth/login", json={"usuario": "NO_EXISTE", "password": "algo"})

    assert response.status_code == 401


def test_login_acceso_inactivo(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(
        routes.repository, "get_miembro_by_usuario", lambda cursor, usuario: _fake_miembro(acceso_activo=False)
    )

    response = client.post("/api/auth/login", json={"usuario": "DOVELA_LG", "password": "clave-secreta-1"})

    assert response.status_code == 401


def test_get_current_user_sin_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


def test_get_current_user_token_invalido():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization="Bearer token-invalido")
    assert exc_info.value.status_code == 401


def test_get_current_user_usuario_desactivado(monkeypatch):
    import app.auth.dependencies as dependencies

    monkeypatch.setattr(dependencies, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(dependencies, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(
        dependencies.repository, "get_miembro_by_id", lambda cursor, id: _fake_miembro(acceso_activo=False)
    )

    token = create_access_token(1, "DOVELA_LG", "Luis Gómez", "SCRUM MASTER")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_get_current_user_success(monkeypatch):
    import app.auth.dependencies as dependencies

    monkeypatch.setattr(dependencies, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(dependencies, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(dependencies.repository, "get_miembro_by_id", lambda cursor, id: _fake_miembro())

    token = create_access_token(1, "DOVELA_LG", "Luis Gómez", "SCRUM MASTER")
    usuario_actual = get_current_user(authorization=f"Bearer {token}")

    assert usuario_actual.usuario == "DOVELA_LG"
    assert usuario_actual.codigo_rol_scrum == "SCRUM MASTER"


def test_forgot_password_correo_existente_envia_correo(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_email", lambda cursor, correo: _fake_miembro())
    monkeypatch.setattr(routes.repository, "crear_token_reset", lambda cursor, miembro_id, token_hash, expira_en: 1)

    correos_enviados = []
    monkeypatch.setattr(
        routes, "enviar_correo", lambda destinatario, asunto, cuerpo: correos_enviados.append(destinatario)
    )

    response = client.post("/api/auth/forgot-password", json={"correo_electronico": "luis.gomez@dovela.com"})

    assert response.status_code == 200
    assert correos_enviados == ["luis.gomez@dovela.com"]


def test_forgot_password_correo_inexistente_no_envia_correo(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_email", lambda cursor, correo: None)

    correos_enviados = []
    monkeypatch.setattr(
        routes, "enviar_correo", lambda destinatario, asunto, cuerpo: correos_enviados.append(destinatario)
    )

    response = client.post("/api/auth/forgot-password", json={"correo_electronico": "no-existe@dovela.com"})

    assert response.status_code == 200
    assert correos_enviados == []
    assert response.json()["detail"] == routes._MENSAJE_FORGOT_PASSWORD


def test_reset_password_token_valido(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    registro = {
        "id": 10,
        "miembro_id": 1,
        "expira_en": datetime.now(timezone.utc) + timedelta(minutes=10),
        "usado_en": None,
    }
    monkeypatch.setattr(routes.repository, "get_token_reset", lambda cursor, token_hash: registro)
    monkeypatch.setattr(routes.repository, "set_password_miembro", lambda cursor, miembro_id, password_hash: None)
    marcados = []
    monkeypatch.setattr(routes.repository, "marcar_token_usado", lambda cursor, token_id: marcados.append(token_id))

    response = client.post("/api/auth/reset-password", json={"token": "token-valido", "password_nueva": "nueva-clave-1"})

    assert response.status_code == 200
    assert marcados == [10]


def test_reset_password_token_inexistente(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_token_reset", lambda cursor, token_hash: None)

    response = client.post("/api/auth/reset-password", json={"token": "token-inventado", "password_nueva": "nueva-clave-1"})

    assert response.status_code == 400


def test_reset_password_token_expirado(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    registro = {
        "id": 10,
        "miembro_id": 1,
        "expira_en": datetime.now(timezone.utc) - timedelta(minutes=1),
        "usado_en": None,
    }
    monkeypatch.setattr(routes.repository, "get_token_reset", lambda cursor, token_hash: registro)

    response = client.post("/api/auth/reset-password", json={"token": "token-expirado", "password_nueva": "nueva-clave-1"})

    assert response.status_code == 400


def test_reset_password_token_ya_usado(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    registro = {
        "id": 10,
        "miembro_id": 1,
        "expira_en": datetime.now(timezone.utc) + timedelta(minutes=10),
        "usado_en": datetime.now(timezone.utc),
    }
    monkeypatch.setattr(routes.repository, "get_token_reset", lambda cursor, token_hash: registro)

    response = client.post("/api/auth/reset-password", json={"token": "token-usado", "password_nueva": "nueva-clave-1"})

    assert response.status_code == 400


def test_change_password_success(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_id", lambda cursor, id: _fake_miembro())
    monkeypatch.setattr(routes.repository, "set_password_miembro", lambda cursor, miembro_id, password_hash: None)

    response = client.post(
        "/api/auth/change-password",
        json={"password_actual": "clave-secreta-1", "password_nueva": "clave-nueva-2"},
    )

    assert response.status_code == 200


def test_change_password_actual_incorrecta(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_id", lambda cursor, id: _fake_miembro())

    response = client.post(
        "/api/auth/change-password",
        json={"password_actual": "clave-equivocada", "password_nueva": "clave-nueva-2"},
    )

    # 400 y no 401: un typo de contraseña actual no debe disparar el logout automático
    # del frontend (que trata cualquier 401 como sesión expirada).
    assert response.status_code == 400

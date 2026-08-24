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

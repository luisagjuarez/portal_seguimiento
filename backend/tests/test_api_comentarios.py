from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user
import app.api.routes_comentarios as routes


class _FakeCursor:
    pass


class _FakeConnection:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return _FakeCursor()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


client = TestClient(app)


def _fake_comentario(comentario_id=1):
    return {
        "id": comentario_id,
        "solicitud_id": 1,
        "tarea_id": 1,
        "tarea_nombre": "Levantar requerimientos",
        "texto_comentario": "Comentario editado.",
        "creado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "creado_por": "dovela_control",
        "creado_por_nombre": "Ramon Rosales",
        "actualizado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "actualizado_por": "dovela_control",
    }


def test_actualizar_comentario_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "update_comentario", lambda cursor, id, texto, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))

    response = client.put("/api/comentarios/1", json={"texto_comentario": "Comentario editado."})

    assert response.status_code == 200
    assert response.json()["texto_comentario"] == "Comentario editado."
    assert fake_conn.committed is True


def test_actualizar_comentario_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: None)

    response = client.put("/api/comentarios/999", json={"texto_comentario": "No existe"})

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_actualizar_comentario_403_si_no_es_autor_ni_scrum_master(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))

    otro_usuario = UsuarioActual(
        id=2, usuario="DOVELA_WA", nombre_completo="Wilber Alegria",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: otro_usuario
    try:
        response = client.put("/api/comentarios/1", json={"texto_comentario": "Intento ajeno"})
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


def test_borrar_comentario_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))
    monkeypatch.setattr(routes.repository, "delete_comentario", lambda cursor, id, **kwargs: 1)

    response = client.delete("/api/comentarios/1")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_borrar_comentario_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: None)

    response = client.delete("/api/comentarios/999")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_comentario_403_si_no_es_autor_ni_scrum_master(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))

    otro_usuario = UsuarioActual(
        id=2, usuario="DOVELA_WA", nombre_completo="Wilber Alegria",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: otro_usuario
    try:
        response = client.delete("/api/comentarios/1")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


def test_actualizar_comentario_200_si_es_el_autor(monkeypatch):
    """El autor real del comentario ("dovela_control" en _fake_comentario) puede editar el
    suyo aunque no sea Scrum Master."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))
    monkeypatch.setattr(routes.repository, "update_comentario", lambda cursor, id, texto, **kwargs: 1)

    autor = UsuarioActual(
        id=3, usuario="dovela_control", nombre_completo="Ramon Rosales",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: autor
    try:
        response = client.put("/api/comentarios/1", json={"texto_comentario": "Editado por su autor"})
        assert response.status_code == 200
    finally:
        del app.dependency_overrides[get_current_user]

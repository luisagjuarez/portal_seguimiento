from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user
import app.api.routes_tarea_por_hacer as routes


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


def _fake_por_hacer(item_id=1, esta_completa=True):
    return {
        "id": item_id,
        "solicitud_id": 1,
        "tarea_id": 1,
        "tarea_nombre": "Levantar requerimientos",
        "responsable_id": 6,
        "responsable": "Ramon Rosales",
        "nombre": "Revisar checklist de despliegue",
        "descripcion": "Confirmar variables de entorno",
        "esta_completa": esta_completa,
        "creado_en": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "creado_por": "DOVELA_LG",
        "creado_por_nombre": "Luis Gómez",
        "actualizado_en": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "actualizado_por": "DOVELA_LG",
    }


def test_actualizar_por_hacer_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "update_por_hacer", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: _fake_por_hacer(id))

    response = client.put(
        "/api/tarea-por-hacer/1",
        json={"nombre": "Revisar checklist de despliegue", "descripcion": "Confirmar variables de entorno", "esta_completa": True},
    )

    assert response.status_code == 200
    assert response.json()["esta_completa"] is True
    assert fake_conn.committed is True


def test_actualizar_por_hacer_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: None)

    response = client.put("/api/tarea-por-hacer/999", json={"nombre": "No existe"})

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_actualizar_por_hacer_403_si_no_es_autor_ni_scrum_master(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: _fake_por_hacer(id))

    otro_usuario = UsuarioActual(
        id=2, usuario="DOVELA_WA", nombre_completo="Wilber Alegria",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: otro_usuario
    try:
        response = client.put("/api/tarea-por-hacer/1", json={"nombre": "Intento ajeno"})
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


def test_actualizar_por_hacer_200_si_es_el_autor(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: _fake_por_hacer(id))
    monkeypatch.setattr(routes.repository, "update_por_hacer", lambda cursor, id, **kwargs: 1)

    autor = UsuarioActual(
        id=1, usuario="DOVELA_LG", nombre_completo="Luis Gómez",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: autor
    try:
        response = client.put(
            "/api/tarea-por-hacer/1",
            json={"nombre": "Revisar checklist de despliegue", "esta_completa": True},
        )
        assert response.status_code == 200
    finally:
        del app.dependency_overrides[get_current_user]


def test_borrar_por_hacer_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: _fake_por_hacer(id))
    monkeypatch.setattr(routes.repository, "delete_por_hacer", lambda cursor, id: 1)

    response = client.delete("/api/tarea-por-hacer/1")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_borrar_por_hacer_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: None)

    response = client.delete("/api/tarea-por-hacer/999")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_por_hacer_403_si_no_es_autor_ni_scrum_master(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: _fake_por_hacer(id))

    otro_usuario = UsuarioActual(
        id=2, usuario="DOVELA_WA", nombre_completo="Wilber Alegria",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: otro_usuario
    try:
        response = client.delete("/api/tarea-por-hacer/1")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]

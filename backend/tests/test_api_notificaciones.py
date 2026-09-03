from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.app import app
import app.api.routes_notificaciones as routes


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


def _fake_notificacion(notificacion_id=1, leido_en=None):
    return {
        "id": notificacion_id,
        "tipo": "TAREA_ASIGNADA",
        "mensaje": "Se te asignó la tarea 'Levantar requerimientos'",
        "entidad_tipo": "TAREA",
        "entidad_id": 1,
        "leido_en": leido_en,
        "creado_en": datetime(2026, 9, 2, tzinfo=timezone.utc),
    }


def test_listar_notificaciones(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(
        routes.repository, "list_notificaciones_by_destinatario", lambda cursor, miembro_id, solo_no_leidas=False, limit=50: [_fake_notificacion()]
    )

    response = client.get("/api/notificaciones")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["tipo"] == "TAREA_ASIGNADA"


def test_contar_notificaciones_no_leidas(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "count_no_leidas", lambda cursor, miembro_id: 3)

    response = client.get("/api/notificaciones/no-leidas/count")

    assert response.status_code == 200
    assert response.json() == {"no_leidas": 3}


def test_marcar_notificacion_leida_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "marcar_notificacion_leida", lambda cursor, id, miembro_id: 1)

    response = client.put("/api/notificaciones/1/leer")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_marcar_notificacion_leida_404(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "marcar_notificacion_leida", lambda cursor, id, miembro_id: 0)

    response = client.put("/api/notificaciones/999/leer")

    assert response.status_code == 404


def test_marcar_todas_notificaciones_leidas(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "marcar_todas_notificaciones_leidas", lambda cursor, miembro_id: 5)

    response = client.put("/api/notificaciones/leer-todas")

    assert response.status_code == 204
    assert fake_conn.committed is True

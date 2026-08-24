from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.app import app
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
        "texto_comentario": "Comentario editado.",
        "creado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "creado_por": "dovela_control",
        "actualizado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "actualizado_por": "dovela_control",
    }


def test_actualizar_comentario_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "update_comentario", lambda cursor, id, texto: 1)
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))

    response = client.put("/api/comentarios/1", json={"texto_comentario": "Comentario editado."})

    assert response.status_code == 200
    assert response.json()["texto_comentario"] == "Comentario editado."
    assert fake_conn.committed is True


def test_actualizar_comentario_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "update_comentario", lambda cursor, id, texto: 0)

    response = client.put("/api/comentarios/999", json={"texto_comentario": "No existe"})

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_comentario_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_comentario", lambda cursor, id: 1)

    response = client.delete("/api/comentarios/1")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_borrar_comentario_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_comentario", lambda cursor, id: 0)

    response = client.delete("/api/comentarios/999")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True

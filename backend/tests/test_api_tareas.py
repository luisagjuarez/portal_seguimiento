from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.app import app
import app.api.routes_tareas as routes


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


def _fake_tarea(tarea_id=1):
    return {
        "id": tarea_id,
        "solicitud_id": 1,
        "nombre": "Levantar requerimientos",
        "descripcion": "Reunión con el cliente",
        "responsable_id": 6,
        "responsable": "Ramon Rosales",
        "esta_completa": "Y",
        "fecha_inicio": date(2026, 8, 23),
        "fecha_fin": date(2026, 8, 30),
        "horas_estimadas": None,
        "horas_reales": None,
        "creado_en": datetime(2026, 8, 23, tzinfo=timezone.utc),
        "actualizado_en": datetime(2026, 8, 23, tzinfo=timezone.utc),
    }


def test_actualizar_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "update_tarea", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    response = client.put(
        "/api/tareas/1",
        json={
            "nombre": "Levantar requerimientos",
            "descripcion": "Reunión con el cliente",
            "responsable_id": 6,
            "esta_completa": "Y",
        },
    )

    assert response.status_code == 200
    assert response.json()["esta_completa"] == "Y"
    assert fake_conn.committed is True


def test_actualizar_tarea_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "update_tarea", lambda cursor, id, **kwargs: 0)

    response = client.put(
        "/api/tareas/999",
        json={"nombre": "No existe", "descripcion": None, "responsable_id": None, "esta_completa": "N"},
    )

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_tarea", lambda cursor, id: 1)

    response = client.delete("/api/tareas/1")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_borrar_tarea_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_tarea", lambda cursor, id: 0)

    response = client.delete("/api/tareas/999")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True

from fastapi.testclient import TestClient

from app.api.app import app
import app.api.routes_catalogos as routes


class _FakeCursor:
    pass


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()

    def close(self):
        pass


client = TestClient(app)


def test_listar_miembros_equipo(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(
        routes.repository,
        "list_miembros",
        lambda cursor: [{"id": 1, "nombre_completo": "Ramon Rosales", "correo_electronico": "ramon@x.com"}],
    )

    response = client.get("/api/miembros-equipo")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "nombre_completo": "Ramon Rosales", "correo_electronico": "ramon@x.com"}
    ]


def test_listar_tipos_solicitud(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_tipos_solicitud", lambda cursor: [{"id": 3, "tipo": "Nuevo"}])

    response = client.get("/api/tipos-solicitud")

    assert response.status_code == 200
    assert response.json() == [{"id": 3, "tipo": "Nuevo"}]


def test_listar_estatus(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(
        routes.repository,
        "list_estatus",
        lambda cursor: [{"codigo": "EN ESPERA", "descripcion": "En espera"}],
    )

    response = client.get("/api/estatus")

    assert response.status_code == 200
    assert response.json() == [{"codigo": "EN ESPERA", "descripcion": "En espera"}]

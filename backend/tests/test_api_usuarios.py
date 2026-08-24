from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import require_scrum_master
import app.api.routes_usuarios as routes

client = TestClient(app)


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


def _fake_miembro_acceso(miembro_id=2):
    return {
        "id": miembro_id,
        "usuario": "DOVELA_WA",
        "nombre_completo": "Wilber Alegria",
        "codigo_rol_scrum": "TEAM",
        "rol_scrum_descripcion": "Team",
        "acceso_activo": True,
    }


def test_listar_usuarios_success(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_miembros_con_acceso", lambda cursor: [_fake_miembro_acceso()])

    response = client.get("/api/usuarios")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["usuario"] == "DOVELA_WA"
    assert "password_hash" not in body[0]


def _denegar_scrum_master():
    raise HTTPException(status_code=403, detail="Solo el Scrum Master puede hacer esto")


def test_listar_usuarios_403_si_no_es_scrum_master():
    app.dependency_overrides[require_scrum_master] = _denegar_scrum_master
    try:
        response = client.get("/api/usuarios")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master]


def test_otorgar_acceso_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_id", lambda cursor, id: {**_fake_miembro_acceso(id), "acceso_activo": False})
    monkeypatch.setattr(routes.repository, "otorgar_acceso_miembro", lambda cursor, id, password_hash, codigo_rol_scrum: 1)
    monkeypatch.setattr(routes.repository, "list_miembros_con_acceso", lambda cursor: [_fake_miembro_acceso()])

    response = client.post("/api/usuarios/2/acceso", json={"password": "clave-inicial-1", "codigo_rol_scrum": "TEAM"})

    assert response.status_code == 201
    assert fake_conn.committed is True


def test_otorgar_acceso_409_si_ya_tiene(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_id", lambda cursor, id: _fake_miembro_acceso(id))

    response = client.post("/api/usuarios/2/acceso", json={"password": "clave-inicial-1", "codigo_rol_scrum": "TEAM"})

    assert response.status_code == 409
    assert fake_conn.rolled_back is True


def test_otorgar_acceso_404_si_no_existe(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_miembro_by_id", lambda cursor, id: None)

    response = client.post("/api/usuarios/999/acceso", json={"password": "clave-inicial-1", "codigo_rol_scrum": "TEAM"})

    assert response.status_code == 404


def test_actualizar_acceso_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "actualizar_acceso_miembro", lambda cursor, id, *args, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "list_miembros_con_acceso", lambda cursor: [_fake_miembro_acceso()])

    response = client.put("/api/usuarios/2/acceso", json={"acceso_activo": False})

    assert response.status_code == 200
    assert fake_conn.committed is True


def test_actualizar_acceso_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "actualizar_acceso_miembro", lambda cursor, id, *args, **kwargs: 0)

    response = client.put("/api/usuarios/999/acceso", json={"acceso_activo": False})

    assert response.status_code == 404
    assert fake_conn.rolled_back is True

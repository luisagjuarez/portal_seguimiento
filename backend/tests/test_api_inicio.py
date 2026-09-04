from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user
import app.api.routes_inicio as routes

client = TestClient(app)


class _FakeCursor:
    pass


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()


def _fake_resumen(total_por_nivel=1):
    return {
        "total": 3,
        "por_estatus": [
            {"valor": "EN ESPERA", "descripcion": "En espera", "total": 3},
            {"valor": "PLANEADO", "descripcion": "Planeado", "total": 0},
        ],
        "por_prioridad": [
            {"valor": str(nivel), "descripcion": "Media", "total": total_por_nivel if nivel == 3 else 0}
            for nivel in range(1, 6)
        ],
    }


def _usuario(codigo_rol_scrum, id=1):
    return UsuarioActual(
        id=id,
        usuario="DOVELA_XX",
        nombre_completo="Usuario de Prueba",
        codigo_rol_scrum=codigo_rol_scrum,
        correo_electronico=None,
        debe_cambiar_password=False,
    )


def _con_usuario(usuario):
    app.dependency_overrides[get_current_user] = lambda: usuario


def _limpiar_override():
    del app.dependency_overrides[get_current_user]


def test_resumen_inicio_scrum_master_ve_totales(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(routes.repository, "get_resumen_solicitudes", lambda cursor, **kwargs: _fake_resumen())
    monkeypatch.setattr(routes.repository, "get_resumen_tareas", lambda cursor, **kwargs: _fake_resumen())

    _con_usuario(_usuario("SCRUM MASTER"))
    try:
        response = client.get("/api/inicio/resumen")
    finally:
        _limpiar_override()

    assert response.status_code == 200
    body = response.json()
    assert body["solicitudes_totales"]["total"] == 3
    assert body["tareas_totales"]["total"] == 3
    assert body["mis_solicitudes"] is None
    assert body["solicitudes_responsable"] is None
    assert body["mis_tareas"] is None


def test_resumen_inicio_product_owner_ve_totales(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(routes.repository, "get_resumen_solicitudes", lambda cursor, **kwargs: _fake_resumen())
    monkeypatch.setattr(routes.repository, "get_resumen_tareas", lambda cursor, **kwargs: _fake_resumen())

    _con_usuario(_usuario("PRODUCT OWNER"))
    try:
        response = client.get("/api/inicio/resumen")
    finally:
        _limpiar_override()

    assert response.status_code == 200
    body = response.json()
    assert body["solicitudes_totales"] is not None
    assert body["mis_solicitudes"] is None


def test_resumen_inicio_team_ve_sus_propios_bloques(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)

    llamadas_solicitudes = []
    llamadas_tareas = []

    def _fake_solicitudes(cursor, **kwargs):
        llamadas_solicitudes.append(kwargs)
        return _fake_resumen()

    def _fake_tareas(cursor, **kwargs):
        llamadas_tareas.append(kwargs)
        return _fake_resumen()

    monkeypatch.setattr(routes.repository, "get_resumen_solicitudes", _fake_solicitudes)
    monkeypatch.setattr(routes.repository, "get_resumen_tareas", _fake_tareas)

    _con_usuario(_usuario("TEAM", id=7))
    try:
        response = client.get("/api/inicio/resumen")
    finally:
        _limpiar_override()

    assert response.status_code == 200
    body = response.json()
    assert body["solicitudes_totales"] is None
    assert body["tareas_totales"] is None
    assert body["mis_solicitudes"]["total"] == 3
    assert body["solicitudes_responsable"]["total"] == 3
    assert body["mis_tareas"]["total"] == 3
    assert llamadas_solicitudes == [{"solicitante_id": 7}, {"responsable_atencion_id": 7}]
    assert llamadas_tareas == [{"responsable_id": 7}]


def test_resumen_inicio_externo_ve_solo_mis_solicitudes(monkeypatch):
    """Punto 2 (2026-09-04): a diferencia de TEAM, un Externo solo recibe mis_solicitudes — los
    otros 2 bloques ni se piden (siempre serían 0, un Externo nunca es responsable de nada)."""
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)

    llamadas_solicitudes = []
    llamadas_tareas = []
    monkeypatch.setattr(
        routes.repository,
        "get_resumen_solicitudes",
        lambda cursor, **kwargs: (llamadas_solicitudes.append(kwargs), _fake_resumen())[1],
    )
    monkeypatch.setattr(
        routes.repository, "get_resumen_tareas", lambda cursor, **kwargs: (llamadas_tareas.append(kwargs), _fake_resumen())[1]
    )

    _con_usuario(_usuario("EXTERNO", id=9))
    try:
        response = client.get("/api/inicio/resumen")
    finally:
        _limpiar_override()

    assert response.status_code == 200
    body = response.json()
    assert body["mis_solicitudes"] is not None
    assert body["solicitudes_responsable"] is None
    assert body["mis_tareas"] is None
    assert body["solicitudes_totales"] is None
    assert body["tareas_totales"] is None
    assert llamadas_solicitudes == [{"solicitante_id": 9}]
    assert llamadas_tareas == []

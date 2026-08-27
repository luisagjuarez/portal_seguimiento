from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user, require_scrum_master_or_product_owner
import app.api.routes_monitor as routes

client = TestClient(app)


class _FakeCursor:
    pass


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()


def _fake_vencida():
    return {
        "id": 1,
        "solicitud_id": 1,
        "solicitud_nombre": "Migración al Nuevo HSM",
        "cliente": "PAC",
        "nombre": "Despliegue en ambiente de TEST",
        "responsable_id": 4,
        "responsable": "Sergio Mariano",
        "codigo_estatus_tarea": "POR HACER",
        "estatus_tarea_descripcion": "Por hacer",
        "fecha_fin": "2026-08-20",
        "dias": 6,
    }


def _fake_cumplimiento():
    return {
        "total_con_fecha_real": 10,
        "cumplidas": 7,
        "atrasadas": 3,
        "porcentaje_cumplimiento": 70.0,
        "promedio_dias_atraso": 2.5,
    }


def _mockear_repository(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(routes.repository, "list_tareas_vencidas", lambda cursor, hoy: [_fake_vencida()])
    monkeypatch.setattr(routes.repository, "list_tareas_por_vencer", lambda cursor, hoy: [])
    monkeypatch.setattr(
        routes.repository,
        "list_carga_por_responsable",
        lambda cursor: [{"responsable_id": 4, "responsable": "Sergio Mariano", "tareas_abiertas": 3}],
    )
    monkeypatch.setattr(
        routes.repository,
        "list_distribucion_estatus",
        lambda cursor: [{"codigo_estatus_tarea": "POR HACER", "descripcion": "Por hacer", "total": 5}],
    )
    monkeypatch.setattr(routes.repository, "get_cumplimiento_planeado_real", lambda cursor: _fake_cumplimiento())


def test_monitor_kpis_success(monkeypatch):
    _mockear_repository(monkeypatch)

    response = client.get("/api/monitor/kpis")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "vencidas", "por_vencer", "carga_por_responsable", "distribucion_estatus", "cumplimiento",
    }
    assert len(body["vencidas"]) == 1
    assert body["cumplimiento"]["porcentaje_cumplimiento"] == 70.0


def _denegar_monitor():
    raise HTTPException(status_code=403, detail="Solo el Scrum Master o el Product Owner pueden ver esto")


def test_monitor_kpis_403_si_no_autorizado():
    app.dependency_overrides[require_scrum_master_or_product_owner] = _denegar_monitor
    try:
        response = client.get("/api/monitor/kpis")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master_or_product_owner]


def test_monitor_kpis_permite_product_owner(monkeypatch):
    _mockear_repository(monkeypatch)
    usuario_po = UsuarioActual(
        id=2,
        usuario="DOVELA_JC",
        nombre_completo="Javier Centeno",
        codigo_rol_scrum="PRODUCT OWNER",
        correo_electronico=None,
        debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: usuario_po
    try:
        response = client.get("/api/monitor/kpis")
        assert response.status_code == 200
    finally:
        del app.dependency_overrides[get_current_user]


def test_monitor_kpis_403_para_team(monkeypatch):
    _mockear_repository(monkeypatch)
    usuario_team = UsuarioActual(
        id=3,
        usuario="DOVELA_WA",
        nombre_completo="Wilber Alegria",
        codigo_rol_scrum="TEAM",
        correo_electronico=None,
        debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: usuario_team
    try:
        response = client.get("/api/monitor/kpis")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]

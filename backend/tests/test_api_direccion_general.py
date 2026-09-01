from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user, require_scrum_master_or_product_owner
import app.api.routes_direccion_general as routes

client = TestClient(app)


class _FakeCursor:
    pass


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()


def _fake_totales():
    return {
        "solicitudes_en_proceso": 12,
        "tareas_en_proceso": 30,
        "solicitudes_concluidas_periodo": 4,
        "tareas_concluidas_periodo": 9,
        "solicitudes_nuevas_periodo": 5,
        "tareas_nuevas_periodo": 11,
        "horas_estimadas_periodo": 80,
    }


def _fake_grupo(grupo_id, grupo):
    return {
        "grupo_id": grupo_id,
        "grupo": grupo,
        "solicitudes_en_proceso": 2,
        "solicitudes_concluidas_periodo": 1,
        "solicitudes_nuevas_periodo": 1,
        "tareas_en_proceso": 3,
        "tareas_concluidas_periodo": 2,
        "tareas_nuevas_periodo": 2,
        "horas_estimadas_periodo": 16,
    }


def _mockear_repository(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(routes.repository, "get_direccion_general_totales", lambda cursor, desde, hasta: _fake_totales())
    monkeypatch.setattr(
        routes.repository,
        "list_direccion_general_por_cliente",
        lambda cursor, desde, hasta: [_fake_grupo(10, "CHANTILLY")],
    )
    monkeypatch.setattr(
        routes.repository,
        "list_direccion_general_por_tipo",
        lambda cursor, desde, hasta: [_fake_grupo(3, "Nuevo")],
    )
    monkeypatch.setattr(
        routes.repository,
        "list_direccion_general_por_area",
        lambda cursor, desde, hasta: [_fake_grupo("Desarrollador", "Desarrollador")],
    )
    monkeypatch.setattr(
        routes.repository,
        "list_distribucion_estatus_solicitud",
        lambda cursor: [{"codigo_estatus": "EN PROGRESO", "descripcion": "En progreso", "total": 12}],
    )
    monkeypatch.setattr(
        routes.repository,
        "list_distribucion_estatus",
        lambda cursor: [{"codigo_estatus_tarea": "EN PROGRESO", "descripcion": "En progreso", "total": 30}],
    )


def test_direccion_general_kpis_success(monkeypatch):
    _mockear_repository(monkeypatch)

    response = client.get("/api/direccion-general/kpis", params={"desde": "2026-08-01", "hasta": "2026-08-31"})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "totales", "por_cliente", "por_tipo", "por_area", "solicitudes_por_estatus", "tareas_por_estatus",
    }
    assert body["totales"]["horas_estimadas_periodo"] == 80
    assert body["por_cliente"][0]["grupo"] == "CHANTILLY"
    assert body["por_area"][0]["grupo"] == "Desarrollador"


def test_direccion_general_kpis_400_si_hasta_antes_de_desde(monkeypatch):
    _mockear_repository(monkeypatch)

    response = client.get("/api/direccion-general/kpis", params={"desde": "2026-08-31", "hasta": "2026-08-01"})

    assert response.status_code == 400


def _denegar():
    raise HTTPException(status_code=403, detail="Solo el Scrum Master o el Product Owner pueden ver esto")


def test_direccion_general_kpis_403_si_no_autorizado():
    app.dependency_overrides[require_scrum_master_or_product_owner] = _denegar
    try:
        response = client.get("/api/direccion-general/kpis", params={"desde": "2026-08-01", "hasta": "2026-08-31"})
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master_or_product_owner]


def test_direccion_general_kpis_permite_product_owner(monkeypatch):
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
        response = client.get("/api/direccion-general/kpis", params={"desde": "2026-08-01", "hasta": "2026-08-31"})
        assert response.status_code == 200
    finally:
        del app.dependency_overrides[get_current_user]


def test_direccion_general_kpis_403_para_team(monkeypatch):
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
        response = client.get("/api/direccion-general/kpis", params={"desde": "2026-08-01", "hasta": "2026-08-31"})
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]

import pytest
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
        "solicitudes_concluidas_periodo": 4,
        "solicitudes_nuevas_periodo": 5,
    }


def _fake_grupo(grupo_id, grupo):
    """Fila completa (solicitudes + tareas) — la sigue devolviendo `list_direccion_general_por_tipo`."""
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


def _fake_grupo_solicitudes(grupo_id, grupo):
    """Fila solo-solicitudes — la devuelven `list_direccion_general_por_cliente`/`por_area`
    desde la Fase 1.25."""
    return {
        "grupo_id": grupo_id,
        "grupo": grupo,
        "solicitudes_en_proceso": 2,
        "solicitudes_concluidas_periodo": 1,
        "solicitudes_nuevas_periodo": 1,
        "solicitudes_en_espera": 1,
    }


def _mockear_repository(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes.repository, "get_direccion_general_totales", lambda cursor, desde, hasta, area: _fake_totales()
    )
    monkeypatch.setattr(
        routes.repository,
        "list_direccion_general_por_cliente",
        lambda cursor, desde, hasta, area: [_fake_grupo_solicitudes(10, "CHANTILLY")],
    )
    monkeypatch.setattr(
        routes.repository,
        "list_direccion_general_por_tipo",
        lambda cursor, desde, hasta, area: [_fake_grupo(3, "Nuevo")],
    )
    monkeypatch.setattr(
        routes.repository,
        "list_direccion_general_por_area",
        lambda cursor, desde, hasta, area: [_fake_grupo_solicitudes("Desarrollador", "Desarrollador")],
    )
    monkeypatch.setattr(
        routes.repository,
        "list_distribucion_estatus_solicitud",
        lambda cursor, area: [{"codigo_estatus": "EN PROGRESO", "descripcion": "En progreso", "total": 12}],
    )


def test_direccion_general_kpis_success(monkeypatch):
    _mockear_repository(monkeypatch)

    response = client.get("/api/direccion-general/kpis", params={"desde": "2026-08-01", "hasta": "2026-08-31"})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "totales", "por_cliente", "por_tipo", "por_area", "solicitudes_por_estatus",
    }
    assert "tareas_en_proceso" not in body["totales"]
    assert body["por_cliente"][0]["grupo"] == "CHANTILLY"
    assert body["por_cliente"][0]["solicitudes_en_espera"] == 1
    assert body["por_area"][0]["grupo"] == "Desarrollador"


def test_direccion_general_kpis_propaga_filtro_area(monkeypatch):
    areas_recibidas = []
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes.repository,
        "get_direccion_general_totales",
        lambda cursor, desde, hasta, area: areas_recibidas.append(area) or _fake_totales(),
    )
    monkeypatch.setattr(routes.repository, "list_direccion_general_por_cliente", lambda cursor, desde, hasta, area: [])
    monkeypatch.setattr(routes.repository, "list_direccion_general_por_tipo", lambda cursor, desde, hasta, area: [])
    monkeypatch.setattr(routes.repository, "list_direccion_general_por_area", lambda cursor, desde, hasta, area: [])
    monkeypatch.setattr(routes.repository, "list_distribucion_estatus_solicitud", lambda cursor, area: [])

    response = client.get(
        "/api/direccion-general/kpis",
        params={"desde": "2026-08-01", "hasta": "2026-08-31", "area": "Desarrollador"},
    )

    assert response.status_code == 200
    assert areas_recibidas == ["Desarrollador"]


def test_direccion_general_kpis_area_es_opcional(monkeypatch):
    _mockear_repository(monkeypatch)

    response = client.get("/api/direccion-general/kpis", params={"desde": "2026-08-01", "hasta": "2026-08-31"})

    assert response.status_code == 200


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


def _fake_solicitud_detalle():
    return {
        "id": 48,
        "nombre": "Reporte de ventas",
        "cliente": "CHANTILLY",
        "area": "Desarrollador",
        "solicitante": "Victor Castañeda",
        "creado_en": "2026-08-15T10:00:00",
    }


def _mockear_detalle(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes.repository,
        "list_direccion_general_detalle_solicitudes",
        lambda cursor, metrica, desde, hasta, area: [_fake_solicitud_detalle()],
    )


@pytest.mark.parametrize("metrica", ["en_proceso", "concluidas", "nuevas"])
def test_direccion_general_detalle_solicitudes_success(monkeypatch, metrica):
    _mockear_detalle(monkeypatch)

    response = client.get(
        "/api/direccion-general/detalle-solicitudes",
        params={"metrica": metrica, "desde": "2026-08-01", "hasta": "2026-08-31"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "id": 48,
            "nombre": "Reporte de ventas",
            "cliente": "CHANTILLY",
            "area": "Desarrollador",
            "solicitante": "Victor Castañeda",
            "creado_en": "2026-08-15T10:00:00",
        }
    ]


def test_direccion_general_detalle_solicitudes_422_si_metrica_invalida(monkeypatch):
    _mockear_detalle(monkeypatch)

    response = client.get(
        "/api/direccion-general/detalle-solicitudes",
        params={"metrica": "no_existe", "desde": "2026-08-01", "hasta": "2026-08-31"},
    )

    assert response.status_code == 422


def test_direccion_general_detalle_solicitudes_400_si_hasta_antes_de_desde(monkeypatch):
    _mockear_detalle(monkeypatch)

    response = client.get(
        "/api/direccion-general/detalle-solicitudes",
        params={"metrica": "en_proceso", "desde": "2026-08-31", "hasta": "2026-08-01"},
    )

    assert response.status_code == 400


def test_direccion_general_detalle_solicitudes_403_si_no_autorizado():
    app.dependency_overrides[require_scrum_master_or_product_owner] = _denegar
    try:
        response = client.get(
            "/api/direccion-general/detalle-solicitudes",
            params={"metrica": "en_proceso", "desde": "2026-08-01", "hasta": "2026-08-31"},
        )
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master_or_product_owner]


def test_direccion_general_detalle_solicitudes_permite_product_owner(monkeypatch):
    _mockear_detalle(monkeypatch)
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
        response = client.get(
            "/api/direccion-general/detalle-solicitudes",
            params={"metrica": "en_proceso", "desde": "2026-08-01", "hasta": "2026-08-31"},
        )
        assert response.status_code == 200
    finally:
        del app.dependency_overrides[get_current_user]

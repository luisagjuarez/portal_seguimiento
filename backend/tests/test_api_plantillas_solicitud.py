from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import require_scrum_master
import app.api.routes_plantillas_solicitud as routes

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


def _fake_resumen():
    return {
        "id": 1,
        "nombre": "Implementación portal DOVELA Inteligencia Fiscal",
        "tipo_solicitud_id": 3,
        "tipo_solicitud": "Implementación",
        "orden_prioridad_default": 3,
        "cantidad_tareas": 7,
        "activo": True,
    }


def _fake_detalle():
    return {
        "id": 1,
        "nombre": "Implementación portal DOVELA Inteligencia Fiscal",
        "tipo_solicitud_id": 3,
        "tipo_solicitud": "Implementación",
        "descripcion_default": None,
        "orden_prioridad_default": 3,
        "activo": True,
        "tareas": [
            {
                "id": 10,
                "orden": 1,
                "nombre": "Despliegue de ambientes (TEST y PRODUCCIÓN)",
                "descripcion": None,
                "responsable_id": 5,
                "responsable_nombre": "Luis Gómez",
                "offset_inicio_dias": 0,
                "offset_fin_dias": 3,
                "horas_estimadas": None,
            }
        ],
    }


def _denegar_scrum_master():
    raise HTTPException(status_code=403, detail="Solo el Scrum Master puede hacer esto")


def _body_creacion(tareas=None):
    return {
        "nombre": "Implementación portal DOVELA Inteligencia Fiscal",
        "tipo_solicitud_id": 3,
        "orden_prioridad_default": 3,
        "tareas": tareas
        if tareas is not None
        else [
            {
                "nombre": "Despliegue de ambientes (TEST y PRODUCCIÓN)",
                "responsable_id": 5,
                "offset_inicio_dias": 0,
                "offset_fin_dias": 3,
            },
            {
                "nombre": "Sesión de cierre de proyecto",
                "responsable_id": 5,
                "offset_inicio_dias": 11,
                "offset_fin_dias": 12,
            },
        ],
    }


def test_listar_plantillas_visible_a_cualquier_autenticado(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_plantillas_solicitud", lambda cursor, solo_activas: [_fake_resumen()])

    response = client.get("/api/plantillas-solicitud")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["nombre"] == "Implementación portal DOVELA Inteligencia Fiscal"


def test_listar_incluir_inactivas_ignorado_si_no_es_scrum_master(monkeypatch):
    """El usuario autenticado de prueba (conftest) es Scrum Master; para probar que un rol
    distinto no puede ver inactivas, se sobreescribe get_current_user (no require_scrum_master,
    que este endpoint no exige para la lista simple)."""
    from app.auth.dependencies import UsuarioActual, get_current_user

    team = UsuarioActual(
        id=2, usuario="DOVELA_WA", nombre_completo="Wilber Alegría",
        codigo_rol_scrum="TEAM", correo_electronico="wilber@dovela.com", debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: team

    solo_activas_recibido = {}

    def _fake_list(cursor, solo_activas):
        solo_activas_recibido["valor"] = solo_activas
        return [_fake_resumen()]

    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_plantillas_solicitud", _fake_list)

    try:
        response = client.get("/api/plantillas-solicitud", params={"incluir_inactivas": "true"})
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200
    assert solo_activas_recibido["valor"] is True


def test_obtener_plantilla_requiere_scrum_master():
    app.dependency_overrides[require_scrum_master] = _denegar_scrum_master
    try:
        response = client.get("/api/plantillas-solicitud/1")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master]


def test_obtener_plantilla_404(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_plantilla_solicitud_by_id", lambda cursor, id: None)

    response = client.get("/api/plantillas-solicitud/999")

    assert response.status_code == 404


def test_crear_plantilla_requiere_scrum_master():
    app.dependency_overrides[require_scrum_master] = _denegar_scrum_master
    try:
        response = client.post("/api/plantillas-solicitud", json=_body_creacion())
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master]


def test_crear_plantilla_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_tipos_solicitud", lambda cursor: [{"id": 3, "tipo": "Implementación"}])
    monkeypatch.setattr(routes.repository, "es_miembro_externo", lambda cursor, id: False)
    monkeypatch.setattr(routes.repository, "insert_plantilla_solicitud", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_plantilla_solicitud_by_id", lambda cursor, id: _fake_detalle())

    response = client.post("/api/plantillas-solicitud", json=_body_creacion())

    assert response.status_code == 201
    assert fake_conn.committed is True
    body = response.json()
    assert len(body["tareas"]) == 1


def test_crear_plantilla_tipo_no_encontrado(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_tipos_solicitud", lambda cursor: [{"id": 99, "tipo": "Otro"}])

    response = client.post("/api/plantillas-solicitud", json=_body_creacion())

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_crear_plantilla_responsable_externo_rechazado(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_tipos_solicitud", lambda cursor: [{"id": 3, "tipo": "Implementación"}])
    monkeypatch.setattr(routes.repository, "es_miembro_externo", lambda cursor, id: id == 5)
    llamado_insert = {"veces": 0}
    monkeypatch.setattr(
        routes.repository,
        "insert_plantilla_solicitud",
        lambda cursor, **kwargs: llamado_insert.__setitem__("veces", llamado_insert["veces"] + 1) or 1,
    )

    response = client.post("/api/plantillas-solicitud", json=_body_creacion())

    assert response.status_code == 422
    assert fake_conn.rolled_back is True
    assert llamado_insert["veces"] == 0


def test_crear_plantilla_offset_fin_menor_a_inicio_422():
    body = _body_creacion(
        tareas=[
            {"nombre": "Tarea inválida", "responsable_id": 5, "offset_inicio_dias": 5, "offset_fin_dias": 2}
        ]
    )
    response = client.post("/api/plantillas-solicitud", json=body)
    assert response.status_code == 422


def test_actualizar_plantilla_reemplaza_tareas(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_tipos_solicitud", lambda cursor: [{"id": 3, "tipo": "Implementación"}])
    monkeypatch.setattr(routes.repository, "es_miembro_externo", lambda cursor, id: False)
    monkeypatch.setattr(routes.repository, "update_plantilla_solicitud", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_plantilla_solicitud_by_id", lambda cursor, id: _fake_detalle())

    response = client.put("/api/plantillas-solicitud/1", json=_body_creacion())

    assert response.status_code == 200
    assert fake_conn.committed is True


def test_actualizar_plantilla_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_tipos_solicitud", lambda cursor: [{"id": 3, "tipo": "Implementación"}])
    monkeypatch.setattr(routes.repository, "es_miembro_externo", lambda cursor, id: False)
    monkeypatch.setattr(routes.repository, "update_plantilla_solicitud", lambda cursor, id, **kwargs: 0)

    response = client.put("/api/plantillas-solicitud/999", json=_body_creacion())

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_dar_de_baja_plantilla_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "dar_de_baja_plantilla_solicitud", lambda cursor, id, actor: 1)

    response = client.delete("/api/plantillas-solicitud/1")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_dar_de_baja_plantilla_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "dar_de_baja_plantilla_solicitud", lambda cursor, id, actor: 0)

    response = client.delete("/api/plantillas-solicitud/999")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_dar_de_baja_plantilla_requiere_scrum_master():
    app.dependency_overrides[require_scrum_master] = _denegar_scrum_master
    try:
        response = client.delete("/api/plantillas-solicitud/1")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master]

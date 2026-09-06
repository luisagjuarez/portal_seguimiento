from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user
from app.db import repository
import app.api.routes_carga_equipo as routes

client = TestClient(app)


class _FakeCursor:
    pass


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()


def _fake_area():
    return {
        "area": "Desarrollador",
        "miembros": [
            {
                "id": 4,
                "usuario": "DOVELA_SM",
                "nombre_completo": "Sergio Mariano",
                "tareas": [
                    {
                        "id": 10,
                        "solicitud_id": 5,
                        "solicitud_nombre": "Migración al Nuevo HSM",
                        "cliente": "PAC",
                        "nombre": "Despliegue en ambiente de TEST",
                        "descripcion": None,
                        "responsable_id": 4,
                        "responsable": "Sergio Mariano",
                        "solicitud_prioridad": 1,
                        "solicitud_fecha_entrega": None,
                        "solicitud_codigo_estatus": "EN PROGRESO",
                        "codigo_estatus_tarea": "EN PROGRESO",
                        "estatus_tarea_descripcion": "En progreso",
                        "fecha_inicio": "2026-09-01",
                        "fecha_fin": "2026-09-10",
                        "fecha_inicio_real": None,
                        "fecha_fin_real": None,
                        "horas_estimadas": 8,
                        "horas_reales": None,
                        "creado_en": "2026-09-01T10:00:00",
                        "actualizado_en": "2026-09-01T10:00:00",
                    }
                ],
            },
            {"id": 7, "usuario": "DOVELA_MM", "nombre_completo": "Marisol Mora", "tareas": []},
        ],
    }


def test_carga_equipo_success(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(routes.repository, "get_carga_equipo", lambda cursor: [_fake_area()])

    response = client.get("/api/carga-equipo")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["area"] == "Desarrollador"
    assert len(body[0]["miembros"]) == 2
    assert len(body[0]["miembros"][0]["tareas"]) == 1
    assert body[0]["miembros"][1]["tareas"] == []


def test_carga_equipo_403_para_externo(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(routes.repository, "get_carga_equipo", lambda cursor: [])
    usuario_externo = UsuarioActual(
        id=8,
        usuario="DOVELA_EXT",
        nombre_completo="Cliente Externo",
        codigo_rol_scrum="EXTERNO",
        correo_electronico=None,
        debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: usuario_externo
    try:
        response = client.get("/api/carga-equipo")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


def test_carga_equipo_permite_team(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: None)
    monkeypatch.setattr(routes.repository, "get_carga_equipo", lambda cursor: [])
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
        response = client.get("/api/carga-equipo")
        assert response.status_code == 200
    finally:
        del app.dependency_overrides[get_current_user]


class _FakeCursorAlertas:
    """Simula la tabla `alertas_sin_tarea_activa` con un set en memoria, para probar el dedup
    de `repository.sincronizar_alertas_sin_tarea_activa` sin una BD real."""

    def __init__(self, marcados_iniciales):
        self.marcados = set(marcados_iniciales)
        self._ultimo_resultado = []

    def execute(self, sql, params=None):
        sql_normalizado = " ".join(sql.split())
        if sql_normalizado.startswith("SELECT miembro_id FROM alertas_sin_tarea_activa"):
            self._ultimo_resultado = [(id_,) for id_ in self.marcados]
        elif sql_normalizado.startswith("DELETE FROM alertas_sin_tarea_activa"):
            for id_ in params["ids"]:
                self.marcados.discard(id_)
        elif sql_normalizado.startswith("INSERT INTO alertas_sin_tarea_activa"):
            self.marcados.add(params["miembro_id"])
        else:
            raise AssertionError(f"SQL no esperado en el fake: {sql_normalizado}")

    def fetchall(self):
        return self._ultimo_resultado


def test_sincronizar_alertas_notifica_la_primera_vez(monkeypatch):
    cursor = _FakeCursorAlertas(marcados_iniciales=[])
    monkeypatch.setattr(repository, "list_miembros_sin_tarea_en_progreso", lambda c: [7])
    notificaciones = []
    monkeypatch.setattr(
        repository,
        "insert_notificacion",
        lambda c, destinatario_id, tipo, mensaje, **kw: notificaciones.append((destinatario_id, tipo)),
    )

    nuevos = repository.sincronizar_alertas_sin_tarea_activa(cursor)

    assert nuevos == [7]
    assert notificaciones == [(7, "SIN_TAREA_EN_PROGRESO")]
    assert cursor.marcados == {7}


def test_sincronizar_alertas_no_duplica_si_ya_esta_marcado(monkeypatch):
    cursor = _FakeCursorAlertas(marcados_iniciales=[7])
    monkeypatch.setattr(repository, "list_miembros_sin_tarea_en_progreso", lambda c: [7])
    notificaciones = []
    monkeypatch.setattr(
        repository,
        "insert_notificacion",
        lambda c, destinatario_id, tipo, mensaje, **kw: notificaciones.append((destinatario_id, tipo)),
    )

    nuevos = repository.sincronizar_alertas_sin_tarea_activa(cursor)

    assert nuevos == []
    assert notificaciones == []
    assert cursor.marcados == {7}


def test_sincronizar_alertas_borra_marca_al_resolverse(monkeypatch):
    cursor = _FakeCursorAlertas(marcados_iniciales=[7])
    monkeypatch.setattr(repository, "list_miembros_sin_tarea_en_progreso", lambda c: [])
    monkeypatch.setattr(repository, "insert_notificacion", lambda *a, **kw: (_ for _ in ()).throw(AssertionError))

    nuevos = repository.sincronizar_alertas_sin_tarea_activa(cursor)

    assert nuevos == []
    assert cursor.marcados == set()

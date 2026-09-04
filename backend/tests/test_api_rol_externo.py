from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user
import app.api.routes_solicitudes as routes_solicitudes
import app.api.routes_tareas as routes_tareas

client = TestClient(app)


class _FakeConnection:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return object()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def _usuario_externo(id=9):
    return UsuarioActual(
        id=id,
        usuario="EXT_CLIENTE",
        nombre_completo="Cliente Externo",
        codigo_rol_scrum="EXTERNO",
        correo_electronico="cliente@externo.com",
        debe_cambiar_password=False,
    )


def _con_usuario(usuario):
    app.dependency_overrides[get_current_user] = lambda: usuario


def _limpiar_override():
    del app.dependency_overrides[get_current_user]


def _fake_solicitud(solicitante_id=9, codigo_estatus="EN ESPERA"):
    return {
        "id": 1,
        "nombre": "Necesito un reporte",
        "descripcion": "Detalle",
        "cliente": "Chantilly",
        "cliente_id": 10,
        "tipo": "Nuevo",
        "tipo_id": 3,
        "codigo_estatus": codigo_estatus,
        "estatus_descripcion": "En espera",
        "solicitante": "Cliente Externo",
        "solicitante_id": solicitante_id,
        "orden_prioridad": 3,
        "canal": "Formulario",
        "canal_id": 3,
        "fecha_completado": None,
        "fecha_entrega": None,
        "responsable_atencion_id": None,
        "responsable_atencion": None,
        "responsable_atencion_area": "Sin área",
        "sr_ebs": None,
        "creado_en": datetime(2026, 9, 3, tzinfo=timezone.utc),
        "actualizado_en": datetime(2026, 9, 3, tzinfo=timezone.utc),
        "actualizado_por": "EXT_CLIENTE",
    }


# ---------------------------------------------------------------------------------
# Un Externo no tiene ningún acceso a nada a nivel tarea.
# ---------------------------------------------------------------------------------


def test_listar_tareas_403_para_externo(monkeypatch):
    monkeypatch.setattr(routes_tareas, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_tareas, "release_connection", lambda conn: None)
    _con_usuario(_usuario_externo())
    try:
        response = client.get("/api/tareas")
        assert response.status_code == 403
    finally:
        _limpiar_override()


def test_obtener_tarea_403_para_externo(monkeypatch):
    monkeypatch.setattr(routes_tareas, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_tareas, "release_connection", lambda conn: None)
    _con_usuario(_usuario_externo())
    try:
        response = client.get("/api/tareas/1")
        assert response.status_code == 403
    finally:
        _limpiar_override()


def test_listar_hitos_solicitud_403_para_externo(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    _con_usuario(_usuario_externo())
    try:
        response = client.get("/api/solicitudes/1/hitos")
        assert response.status_code == 403
    finally:
        _limpiar_override()


def test_listar_enlaces_solicitud_403_para_externo(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    _con_usuario(_usuario_externo())
    try:
        response = client.get("/api/solicitudes/1/enlaces")
        assert response.status_code == 403
    finally:
        _limpiar_override()


# ---------------------------------------------------------------------------------
# GET /solicitudes fuerza el filtro por su propio id, sin importar lo que mande el query.
# ---------------------------------------------------------------------------------


def test_listar_solicitudes_fuerza_involucrado_id_para_externo(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)

    kwargs_recibidos = {}

    def _fake_list_solicitudes(cursor, **kwargs):
        kwargs_recibidos.update(kwargs)
        return []

    monkeypatch.setattr(routes_solicitudes.repository, "list_solicitudes", _fake_list_solicitudes)

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.get("/api/solicitudes", params={"involucrado_id": 1})
        assert response.status_code == 200
    finally:
        _limpiar_override()

    assert kwargs_recibidos["involucrado_id"] == 9


# ---------------------------------------------------------------------------------
# GET /solicitudes/{id}: 404 si no es propia, 200 si sí.
# ---------------------------------------------------------------------------------


def test_obtener_solicitud_404_si_externo_no_es_propia(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud(solicitante_id=1)
    )

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.get("/api/solicitudes/1")
        assert response.status_code == 404
    finally:
        _limpiar_override()


def test_obtener_solicitud_200_si_externo_es_propia(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud(solicitante_id=9)
    )

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.get("/api/solicitudes/1")
        assert response.status_code == 200
    finally:
        _limpiar_override()


# ---------------------------------------------------------------------------------
# PUT /solicitudes/{id} (staff) queda bloqueado para Externo; debe usar /mi-solicitud.
# ---------------------------------------------------------------------------------


def test_actualizar_solicitud_403_si_es_externo():
    _con_usuario(_usuario_externo())
    try:
        response = client.put(
            "/api/solicitudes/1",
            json={
                "nombre": "x",
                "descripcion": "x",
                "tipo": "Nuevo",
                "canal": "Formulario",
                "codigo_estatus": "EN ESPERA",
            },
        )
        assert response.status_code == 403
    finally:
        _limpiar_override()


# ---------------------------------------------------------------------------------
# PUT /solicitudes/{id}/mi-solicitud: dueño + estatus "EN ESPERA".
# ---------------------------------------------------------------------------------


def test_actualizar_mi_solicitud_404_si_no_es_propia(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud(solicitante_id=1)
    )

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.put(
            "/api/solicitudes/1/mi-solicitud",
            json={"nombre": "Nuevo título", "descripcion": "Detalle", "tipo": "Nuevo"},
        )
        assert response.status_code == 404
    finally:
        _limpiar_override()


def test_actualizar_mi_solicitud_409_si_no_esta_en_espera(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository,
        "get_solicitud_by_id",
        lambda cursor, id: _fake_solicitud(solicitante_id=9, codigo_estatus="EN PROGRESO"),
    )

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.put(
            "/api/solicitudes/1/mi-solicitud",
            json={"nombre": "Nuevo título", "descripcion": "Detalle", "tipo": "Nuevo"},
        )
        assert response.status_code == 409
    finally:
        _limpiar_override()


def test_actualizar_mi_solicitud_success_si_en_espera(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository,
        "get_solicitud_by_id",
        lambda cursor, id: _fake_solicitud(solicitante_id=9, codigo_estatus="EN ESPERA"),
    )
    monkeypatch.setattr(routes_solicitudes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes_solicitudes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes_solicitudes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes_solicitudes.repository, "update_solicitud_externo", lambda cursor, id, **kwargs: 1)

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.put(
            "/api/solicitudes/1/mi-solicitud",
            json={"nombre": "Nuevo título", "descripcion": "Detalle", "tipo": "Nuevo", "cliente": "Chantilly"},
        )
        assert response.status_code == 200
    finally:
        _limpiar_override()
    assert fake_conn.committed is True


# ---------------------------------------------------------------------------------
# POST /solicitudes/{id}/comentarios (nivel solicitud).
# ---------------------------------------------------------------------------------


def test_crear_comentario_solicitud_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud(solicitante_id=9)
    )
    monkeypatch.setattr(routes_solicitudes.repository, "insert_comentario", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(
        routes_solicitudes.repository,
        "get_comentario_by_id",
        lambda cursor, id: {
            "id": id,
            "solicitud_id": 1,
            "tarea_id": None,
            "tarea_nombre": None,
            "texto_comentario": "Gracias por la actualización",
            "creado_en": datetime(2026, 9, 3, tzinfo=timezone.utc),
            "creado_por": "EXT_CLIENTE",
            "creado_por_nombre": "Cliente Externo",
            "actualizado_en": datetime(2026, 9, 3, tzinfo=timezone.utc),
            "actualizado_por": "EXT_CLIENTE",
        },
    )

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.post(
            "/api/solicitudes/1/comentarios", json={"texto_comentario": "Gracias por la actualización"}
        )
        assert response.status_code == 201
    finally:
        _limpiar_override()
    assert response.json()["tarea_id"] is None


def test_crear_comentario_solicitud_menciona_sin_excluir_externos(monkeypatch):
    """Punto 6 (2026-09-04): a nivel solicitud sí se puede arrobar a un Externo — la resolución
    de menciones se pide con excluir_externos=False (a diferencia de comentarios de tarea)."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud(solicitante_id=1)
    )
    monkeypatch.setattr(routes_solicitudes.repository, "insert_comentario", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(
        routes_solicitudes.repository,
        "get_comentario_by_id",
        lambda cursor, id: {
            "id": id,
            "solicitud_id": 1,
            "tarea_id": None,
            "tarea_nombre": None,
            "texto_comentario": "@EXT_CLIENTE ya casi está",
            "creado_en": datetime(2026, 9, 4, tzinfo=timezone.utc),
            "creado_por": "DOVELA_LG",
            "creado_por_nombre": "Luis Gómez",
            "actualizado_en": datetime(2026, 9, 4, tzinfo=timezone.utc),
            "actualizado_por": "DOVELA_LG",
        },
    )

    llamadas = []

    def _fake_find(cursor, usuario, excluir_externos=False):
        llamadas.append(excluir_externos)
        return {"id": 9, "nombre_completo": "Cliente Externo"} if usuario == "EXT_CLIENTE" else None

    monkeypatch.setattr(routes_solicitudes.repository, "find_miembro_activo_by_usuario", _fake_find)

    notificaciones = []
    monkeypatch.setattr(
        routes_solicitudes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append(destinatario_id),
    )

    response = client.post("/api/solicitudes/1/comentarios", json={"texto_comentario": "@EXT_CLIENTE ya casi está"})

    assert response.status_code == 201
    assert llamadas == [False]
    assert notificaciones == [9]


def test_crear_comentario_solicitud_todos_nunca_incluye_externos(monkeypatch):
    """@todos siempre significa "todo el equipo interno", incluso a nivel solicitud — nunca
    debe blastear a un cliente Externo solo por estar activo."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud(solicitante_id=1)
    )
    monkeypatch.setattr(routes_solicitudes.repository, "insert_comentario", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(
        routes_solicitudes.repository,
        "get_comentario_by_id",
        lambda cursor, id: {
            "id": 1,
            "solicitud_id": 1,
            "tarea_id": None,
            "tarea_nombre": None,
            "texto_comentario": "@todos revisen esto",
            "creado_en": datetime(2026, 9, 4, tzinfo=timezone.utc),
            "creado_por": "DOVELA_LG",
            "creado_por_nombre": "Luis Gómez",
            "actualizado_en": datetime(2026, 9, 4, tzinfo=timezone.utc),
            "actualizado_por": "DOVELA_LG",
        },
    )

    llamadas = []
    monkeypatch.setattr(
        routes_solicitudes.repository,
        "list_miembros_activos_ids",
        lambda cursor, excluir_externos=False: (llamadas.append(excluir_externos), [1, 2, 6])[1],
    )
    monkeypatch.setattr(routes_solicitudes.repository, "insert_notificacion", lambda cursor, *args, **kwargs: 1)

    response = client.post("/api/solicitudes/1/comentarios", json={"texto_comentario": "@todos revisen esto"})

    assert response.status_code == 201
    assert llamadas == [True]


def test_crear_comentario_solicitud_404_si_externo_no_es_propia(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud(solicitante_id=1)
    )

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.post("/api/solicitudes/1/comentarios", json={"texto_comentario": "Hola"})
        assert response.status_code == 404
    finally:
        _limpiar_override()


# ---------------------------------------------------------------------------------
# Adjuntos de solicitud: 404 si Externo intenta ver los de otra solicitud.
# ---------------------------------------------------------------------------------


def test_listar_adjuntos_solicitud_404_si_externo_no_es_propia(monkeypatch):
    monkeypatch.setattr(routes_solicitudes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes_solicitudes, "release_connection", lambda conn: None)
    monkeypatch.setattr(
        routes_solicitudes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud(solicitante_id=1)
    )

    _con_usuario(_usuario_externo(id=9))
    try:
        response = client.get("/api/solicitudes/1/adjuntos")
        assert response.status_code == 404
    finally:
        _limpiar_override()

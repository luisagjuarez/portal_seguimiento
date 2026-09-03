from datetime import date, datetime, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user, require_scrum_master
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
        "solicitud_prioridad": 3,
        "solicitud_fecha_entrega": None,
        "solicitud_codigo_estatus": "EN PROGRESO",
        "codigo_estatus_tarea": "COMPLETADO",
        "estatus_tarea_descripcion": "Completado",
        "fecha_inicio": date(2026, 8, 23),
        "fecha_fin": date(2026, 8, 30),
        "fecha_inicio_real": None,
        "fecha_fin_real": None,
        "horas_estimadas": None,
        "horas_reales": None,
        "creado_en": datetime(2026, 8, 23, tzinfo=timezone.utc),
        "actualizado_en": datetime(2026, 8, 23, tzinfo=timezone.utc),
    }


def _fake_tarea_tablero(tarea_id=1):
    fila = _fake_tarea(tarea_id)
    fila["solicitud_nombre"] = "Reporte de gastos"
    fila["cliente"] = "Chantilly"
    return fila


def test_listar_tareas(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())

    filtros_recibidos = {}

    def _fake_list_tareas(cursor, cliente=None, responsable_id=None):
        filtros_recibidos.update({"cliente": cliente, "responsable_id": responsable_id})
        return [_fake_tarea_tablero()]

    monkeypatch.setattr(routes.repository, "list_tareas", _fake_list_tareas)

    response = client.get("/api/tareas", params={"cliente": "chan", "responsable_id": 6})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["solicitud_nombre"] == "Reporte de gastos"
    assert body[0]["cliente"] == "Chantilly"
    assert filtros_recibidos == {"cliente": "chan", "responsable_id": 6}


def test_obtener_tarea_success(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea_tablero(id))

    response = client.get("/api/tareas/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["solicitud_nombre"] == "Reporte de gastos"
    assert response.json()["cliente"] == "Chantilly"


def test_obtener_tarea_404(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: None)

    response = client.get("/api/tareas/999")

    assert response.status_code == 404


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
            "codigo_estatus_tarea": "COMPLETADO",
        },
    )

    assert response.status_code == 200
    assert response.json()["codigo_estatus_tarea"] == "COMPLETADO"
    assert fake_conn.committed is True


def test_actualizar_tarea_pasa_fechas_y_horas_al_repositorio(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    kwargs_recibidos = {}

    def _fake_update_tarea(cursor, id, **kwargs):
        kwargs_recibidos.update(kwargs)
        return 1

    monkeypatch.setattr(routes.repository, "update_tarea", _fake_update_tarea)

    response = client.put(
        "/api/tareas/1",
        json={
            "nombre": "Levantar requerimientos",
            "descripcion": "Reunión con el cliente",
            "responsable_id": 6,
            "codigo_estatus_tarea": "EN PROGRESO",
            "fecha_inicio": "2026-08-24",
            "fecha_fin": "2026-08-28",
            "fecha_inicio_real": "2026-08-25",
            "fecha_fin_real": "2026-08-29",
            "horas_estimadas": 8,
            "horas_reales": 5,
        },
    )

    assert response.status_code == 200
    assert kwargs_recibidos["fecha_inicio"] == date(2026, 8, 24)
    assert kwargs_recibidos["fecha_fin"] == date(2026, 8, 28)
    assert kwargs_recibidos["fecha_inicio_real"] == date(2026, 8, 25)
    assert kwargs_recibidos["fecha_fin_real"] == date(2026, 8, 29)
    assert kwargs_recibidos["horas_estimadas"] == 8
    assert kwargs_recibidos["horas_reales"] == 5


def test_actualizar_tarea_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: None)
    monkeypatch.setattr(routes.repository, "update_tarea", lambda cursor, id, **kwargs: 0)

    response = client.put(
        "/api/tareas/999",
        json={"nombre": "No existe", "descripcion": None, "responsable_id": None, "codigo_estatus_tarea": "POR HACER"},
    )

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_tarea", lambda cursor, id, **kwargs: 1)

    response = client.delete("/api/tareas/1")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_borrar_tarea_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_tarea", lambda cursor, id, **kwargs: 0)

    response = client.delete("/api/tareas/999")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_tarea_403_si_no_es_scrum_master():
    def _denegar_scrum_master():
        raise HTTPException(status_code=403, detail="Solo el Scrum Master puede hacer esto")

    app.dependency_overrides[require_scrum_master] = _denegar_scrum_master
    try:
        response = client.delete("/api/tareas/1")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master]


def _fake_hito(hito_id=1):
    return {
        "id": hito_id,
        "solicitud_id": 1,
        "tarea_id": 1,
        "tarea_nombre": "Levantar requerimientos",
        "nombre": "Entrega beta",
        "descripcion": "Primera entrega al cliente",
        "fecha_vencimiento": date(2026, 9, 15),
        "creado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "creado_por": "DOVELA_LG",
        "creado_por_nombre": "Luis Gómez",
        "actualizado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
    }


def test_obtener_hito_tarea_success(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: _fake_hito())

    response = client.get("/api/tareas/1/hito")

    assert response.status_code == 200
    assert response.json()["nombre"] == "Entrega beta"


def test_obtener_hito_tarea_404_sin_hito(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: None)

    response = client.get("/api/tareas/1/hito")

    assert response.status_code == 404


def test_crear_hito_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_hito_para_tarea", lambda cursor, tarea_id, **kwargs: 1)

    respuestas = [None, _fake_hito()]
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: respuestas.pop(0))

    response = client.post(
        "/api/tareas/1/hito",
        json={"nombre": "Entrega beta", "descripcion": "Primera entrega al cliente", "fecha_vencimiento": "2026-09-15"},
    )

    assert response.status_code == 201
    assert response.json()["nombre"] == "Entrega beta"
    assert fake_conn.committed is True


def test_crear_hito_tarea_409_si_ya_existe(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: _fake_hito())

    response = client.post(
        "/api/tareas/1/hito",
        json={"nombre": "Otro hito", "fecha_vencimiento": "2026-09-15"},
    )

    assert response.status_code == 409
    assert fake_conn.rolled_back is True


def test_crear_hito_tarea_404_si_tarea_no_existe(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: None)

    response = client.post(
        "/api/tareas/999/hito",
        json={"nombre": "Entrega beta", "fecha_vencimiento": "2026-09-15"},
    )

    assert response.status_code == 404


def test_actualizar_hito_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: _fake_hito())
    monkeypatch.setattr(routes.repository, "update_hito", lambda cursor, id, **kwargs: 1)

    response = client.put(
        "/api/tareas/1/hito",
        json={"nombre": "Entrega beta v2", "fecha_vencimiento": "2026-09-20"},
    )

    assert response.status_code == 200
    assert fake_conn.committed is True


def test_actualizar_hito_tarea_404_sin_hito(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: None)

    response = client.put(
        "/api/tareas/1/hito",
        json={"nombre": "Entrega beta", "fecha_vencimiento": "2026-09-15"},
    )

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_hito_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: _fake_hito())
    monkeypatch.setattr(routes.repository, "delete_hito", lambda cursor, id, **kwargs: 1)

    response = client.delete("/api/tareas/1/hito")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_borrar_hito_tarea_404_sin_hito(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: None)

    response = client.delete("/api/tareas/1/hito")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_actualizar_hito_tarea_403_si_no_es_autor_ni_scrum_master(monkeypatch):
    """_fake_hito() tiene creado_por="DOVELA_LG"; un Team distinto no puede editarlo."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: _fake_hito())

    otro_usuario = UsuarioActual(
        id=2, usuario="DOVELA_WA", nombre_completo="Wilber Alegria",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: otro_usuario
    try:
        response = client.put(
            "/api/tareas/1/hito", json={"nombre": "Intento ajeno", "fecha_vencimiento": "2026-09-15"}
        )
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


def test_borrar_hito_tarea_403_si_no_es_autor_ni_scrum_master(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: _fake_hito())

    otro_usuario = UsuarioActual(
        id=2, usuario="DOVELA_WA", nombre_completo="Wilber Alegria",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: otro_usuario
    try:
        response = client.delete("/api/tareas/1/hito")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


def test_actualizar_hito_tarea_200_si_es_el_autor_aunque_no_sea_scrum_master(monkeypatch):
    """_fake_hito() tiene creado_por="DOVELA_LG"; ese mismo usuario, aunque su rol sea Team,
    puede editar su propio hito."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_hito_by_tarea", lambda cursor, id: _fake_hito())
    monkeypatch.setattr(routes.repository, "update_hito", lambda cursor, id, **kwargs: 1)

    autor_no_scrum_master = UsuarioActual(
        id=1, usuario="DOVELA_LG", nombre_completo="Luis Gómez",
        codigo_rol_scrum="TEAM", correo_electronico=None, debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: autor_no_scrum_master
    try:
        response = client.put(
            "/api/tareas/1/hito", json={"nombre": "Entrega beta v2", "fecha_vencimiento": "2026-09-20"}
        )
        assert response.status_code == 200
    finally:
        del app.dependency_overrides[get_current_user]


def _fake_comentario(comentario_id=1, tarea_id=1):
    return {
        "id": comentario_id,
        "solicitud_id": 1,
        "tarea_id": tarea_id,
        "tarea_nombre": "Levantar requerimientos",
        "texto_comentario": "Quedamos en revisar esto el viernes.",
        "creado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "creado_por": "dovela_control",
        "creado_por_nombre": "Ramon Rosales",
        "actualizado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "actualizado_por": "dovela_control",
    }


def test_listar_comentarios_tarea(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_comentarios_by_tarea", lambda cursor, id: [_fake_comentario()])

    response = client.get("/api/tareas/1/comentarios")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_crear_comentario_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_comentario", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))

    response = client.post("/api/tareas/1/comentarios", json={"texto_comentario": "Quedamos en revisar esto el viernes."})

    assert response.status_code == 201
    assert response.json()["texto_comentario"] == "Quedamos en revisar esto el viernes."
    assert fake_conn.committed is True


def test_crear_comentario_tarea_404_si_tarea_no_existe(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: None)

    response = client.post("/api/tareas/999/comentarios", json={"texto_comentario": "Comentario"})

    assert response.status_code == 404


def _fake_enlace(enlace_id=1, tarea_id=1):
    return {
        "id": enlace_id,
        "solicitud_id": 1,
        "tarea_id": tarea_id,
        "tarea_nombre": "Levantar requerimientos",
        "tipo_enlace": "URL",
        "url": "https://ejemplo.com/documento",
        "aplicacion_id": None,
        "pagina_aplicacion": None,
        "descripcion": "Documento de referencia",
        "creado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "creado_por": "DOVELA_LG",
        "creado_por_nombre": "Luis Gómez",
        "actualizado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "actualizado_por": "DOVELA_LG",
    }


def test_listar_enlaces_tarea(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_enlaces_by_tarea", lambda cursor, id: [_fake_enlace()])

    response = client.get("/api/tareas/1/enlaces")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["tipo_enlace"] == "URL"
    assert body[0]["creado_por_nombre"] == "Luis Gómez"


def test_crear_enlace_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_enlace_tarea", lambda cursor, tarea_id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_enlace_tarea_by_id", lambda cursor, id: _fake_enlace(id))

    response = client.post(
        "/api/tareas/1/enlaces",
        json={
            "tipo_enlace": "URL",
            "url": "https://ejemplo.com/documento",
            "descripcion": "Documento de referencia",
        },
    )

    assert response.status_code == 201
    assert response.json()["tipo_enlace"] == "URL"
    assert fake_conn.committed is True


def test_crear_enlace_tarea_404_si_tarea_no_existe(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: None)

    response = client.post("/api/tareas/999/enlaces", json={"tipo_enlace": "URL"})

    assert response.status_code == 404


def test_crear_enlace_tarea_requiere_tipo_enlace():
    response = client.post("/api/tareas/1/enlaces", json={"url": "https://ejemplo.com"})

    assert response.status_code == 422


def _fake_por_hacer(item_id=1, tarea_id=1, esta_completa=False):
    return {
        "id": item_id,
        "solicitud_id": 1,
        "tarea_id": tarea_id,
        "tarea_nombre": "Levantar requerimientos",
        "responsable_id": 6,
        "responsable": "Ramon Rosales",
        "nombre": "Revisar checklist de despliegue",
        "descripcion": "Confirmar variables de entorno",
        "esta_completa": esta_completa,
        "creado_en": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "creado_por": "DOVELA_LG",
        "creado_por_nombre": "Luis Gómez",
        "actualizado_en": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "actualizado_por": "DOVELA_LG",
    }


def test_listar_por_hacer_tarea(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(
        routes.repository, "list_por_hacer_by_tarea", lambda cursor, id: [_fake_por_hacer(esta_completa=True)]
    )

    response = client.get("/api/tareas/1/por-hacer")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["esta_completa"] is True


def test_crear_por_hacer_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    llamada = {}

    def _insert_por_hacer(cursor, tarea_id, **kwargs):
        llamada.update(kwargs)
        return 1

    monkeypatch.setattr(routes.repository, "insert_por_hacer", _insert_por_hacer)
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: _fake_por_hacer(id))

    response = client.post(
        "/api/tareas/1/por-hacer",
        json={"nombre": "Revisar checklist de despliegue", "descripcion": "Confirmar variables de entorno"},
    )

    assert response.status_code == 201
    assert response.json()["nombre"] == "Revisar checklist de despliegue"
    assert response.json()["esta_completa"] is False
    assert llamada["solicitud_id"] == 1
    assert fake_conn.committed is True


def test_crear_por_hacer_tarea_404_si_tarea_no_existe(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: None)

    response = client.post("/api/tareas/999/por-hacer", json={"nombre": "Ítem"})

    assert response.status_code == 404


def test_crear_por_hacer_tarea_notifica_al_responsable(monkeypatch):
    """Fase 1.20: asignar un 'por hacer' a alguien (que no sea quien lo crea) notifica."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_por_hacer", lambda cursor, tarea_id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: _fake_por_hacer(id))

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append((destinatario_id, kwargs)),
    )

    response = client.post(
        "/api/tareas/1/por-hacer",
        json={"nombre": "Revisar checklist", "responsable_id": 6},
    )

    assert response.status_code == 201
    assert len(notificaciones) == 1
    assert notificaciones[0][0] == 6
    assert notificaciones[0][1]["tipo"] == "POR_HACER_ASIGNADO"


def test_crear_por_hacer_tarea_notifica_aunque_el_responsable_sea_quien_crea(monkeypatch):
    """Ajuste: ya no se excluye la auto-notificación al asignarse uno mismo un pendiente."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_por_hacer", lambda cursor, tarea_id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_por_hacer_by_id", lambda cursor, id: _fake_por_hacer(id))

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append(destinatario_id),
    )

    # USUARIO_DE_PRUEBA (conftest) tiene id=1
    response = client.post(
        "/api/tareas/1/por-hacer",
        json={"nombre": "Revisar checklist", "responsable_id": 1},
    )

    assert response.status_code == 201
    assert notificaciones == [1]


def test_crear_comentario_tarea_notifica_mencion(monkeypatch):
    """Fase 1.20: @usuario en el texto del comentario notifica a ese miembro si tiene acceso
    activo."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_comentario", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))
    monkeypatch.setattr(
        routes.repository,
        "find_miembro_activo_by_usuario",
        lambda cursor, usuario: {"id": 6, "nombre_completo": "Ramon Rosales"} if usuario == "DOVELA_WA" else None,
    )

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append((destinatario_id, kwargs)),
    )

    response = client.post(
        "/api/tareas/1/comentarios", json={"texto_comentario": "@DOVELA_WA revisa esto por favor"}
    )

    assert response.status_code == 201
    assert len(notificaciones) == 1
    destinatario_id, kwargs = notificaciones[0]
    assert destinatario_id == 6
    assert kwargs["tipo"] == "MENCION_COMENTARIO"
    assert kwargs["entidad_tipo"] == "TAREA"
    assert kwargs["entidad_id"] == 1


def test_crear_comentario_tarea_notifica_si_el_autor_se_menciona_a_si_mismo(monkeypatch):
    """Ajuste: ya no se excluye la auto-notificación al mencionarse uno mismo con @usuario."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_comentario", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))
    monkeypatch.setattr(
        routes.repository,
        "find_miembro_activo_by_usuario",
        lambda cursor, usuario: {"id": 1, "nombre_completo": "Luis Gómez"} if usuario == "DOVELA_LG" else None,
    )

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append(destinatario_id),
    )

    # USUARIO_DE_PRUEBA (conftest) es DOVELA_LG con id=1
    response = client.post("/api/tareas/1/comentarios", json={"texto_comentario": "@DOVELA_LG me lo anoto"})

    assert response.status_code == 201
    assert notificaciones == [1]


def test_crear_comentario_tarea_notifica_a_todos_con_arroba_todos(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_comentario", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))
    monkeypatch.setattr(routes.repository, "list_miembros_activos_ids", lambda cursor: [1, 2, 6, 9])

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append(destinatario_id),
    )

    response = client.post("/api/tareas/1/comentarios", json={"texto_comentario": "@todos revisen esto"})

    assert response.status_code == 201
    # ajuste: el propio autor (id=1, USUARIO_DE_PRUEBA) también se notifica si queda incluido
    assert sorted(notificaciones) == [1, 2, 6, 9]


def test_crear_comentario_tarea_sin_mencion_no_notifica(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_comentario", lambda cursor, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_comentario_by_id", lambda cursor, id: _fake_comentario(id))

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append(destinatario_id),
    )

    response = client.post("/api/tareas/1/comentarios", json={"texto_comentario": "Sin menciones aquí"})

    assert response.status_code == 201
    assert notificaciones == []


def test_actualizar_tarea_notifica_si_cambia_el_responsable(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    # _fake_tarea() trae responsable_id=6; el body cambia a 9 -> debe notificar a 9
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "update_tarea", lambda cursor, id, **kwargs: 1)

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append(destinatario_id),
    )

    response = client.put(
        "/api/tareas/1",
        json={
            "nombre": "Levantar requerimientos",
            "descripcion": "Reunión con el cliente",
            "responsable_id": 9,
            "codigo_estatus_tarea": "EN PROGRESO",
        },
    )

    assert response.status_code == 200
    assert notificaciones == [9]


# ---------------------------------------------------------------------------------
# Adjuntos en tareas (Fase 1.21) — no existía nada antes de esta fase.
# ---------------------------------------------------------------------------------


def test_listar_adjuntos_tarea(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    fake_adjunto = {
        "id": 1,
        "nombre_archivo": "captura.png",
        "tipo_mime": "image/png",
        "tamano_bytes": 1234,
        "fecha_carga": datetime(2026, 9, 2, tzinfo=timezone.utc),
    }
    monkeypatch.setattr(routes.repository, "list_adjuntos_by_tarea", lambda cursor, id: [fake_adjunto])

    response = client.get("/api/tareas/1/adjuntos")

    assert response.status_code == 200
    assert response.json()[0]["nombre_archivo"] == "captura.png"


def test_agregar_adjuntos_tarea_success(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "count_adjuntos_by_tarea", lambda cursor, id: 0)
    monkeypatch.setattr(routes, "save_attachment", lambda id_tarea, filename, content, subdir="": f"/fake/{filename}")

    guardados = []

    def _fake_insert_adjunto_tarea(cursor, id_tarea, nombre_archivo, ruta, tipo_mime, tamano):
        guardados.append(nombre_archivo)
        return len(guardados)

    monkeypatch.setattr(routes.repository, "insert_adjunto_tarea", _fake_insert_adjunto_tarea)
    monkeypatch.setattr(
        routes.repository,
        "list_adjuntos_by_tarea",
        lambda cursor, id: [
            {
                "id": i + 1,
                "nombre_archivo": nombre,
                "tipo_mime": "text/plain",
                "tamano_bytes": 10,
                "fecha_carga": datetime(2026, 9, 2, tzinfo=timezone.utc),
            }
            for i, nombre in enumerate(guardados)
        ],
    )

    response = client.post("/api/tareas/1/adjuntos", files=[("files", ("nuevo.txt", b"contenido", "text/plain"))])

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["nombre_archivo"] == "nuevo.txt"


def test_agregar_adjuntos_tarea_rechaza_si_pasa_del_maximo(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "count_adjuntos_by_tarea", lambda cursor, id: 5)

    response = client.post("/api/tareas/1/adjuntos", files=[("files", ("otro.txt", b"contenido", "text/plain"))])

    assert response.status_code == 422


def test_agregar_adjuntos_tarea_404_si_no_existe(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: None)

    response = client.post("/api/tareas/999/adjuntos", files=[("files", ("nuevo.txt", b"contenido", "text/plain"))])

    assert response.status_code == 404


def test_descargar_adjunto_tarea_success(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    archivo = tmp_path / "captura.png"
    archivo.write_bytes(b"contenido-fake-png")
    monkeypatch.setattr(
        routes.repository,
        "get_adjunto_de_tarea",
        lambda cursor, tarea_id, adjunto_id: {
            "id": adjunto_id,
            "nombre_archivo": "captura.png",
            "ruta_almacenamiento": str(archivo),
            "tipo_mime": "image/png",
            "tamano_bytes": 19,
        },
    )

    response = client.get("/api/tareas/1/adjuntos/1/descargar")

    assert response.status_code == 200
    assert response.content == b"contenido-fake-png"


def test_descargar_adjunto_tarea_404_si_no_pertenece(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_adjunto_de_tarea", lambda cursor, tarea_id, adjunto_id: None)

    response = client.get("/api/tareas/1/adjuntos/999/descargar")

    assert response.status_code == 404

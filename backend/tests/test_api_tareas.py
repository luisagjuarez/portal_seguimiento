from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.app import app
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

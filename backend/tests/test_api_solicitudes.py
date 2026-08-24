from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.app import app
import app.api.routes_solicitudes as routes


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


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_buscar_clientes(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "search_cliente_names", lambda cursor, q: ["Chantilly"])

    response = client.get("/api/clientes", params={"q": "chan"})

    assert response.status_code == 200
    assert response.json() == [{"nombre": "Chantilly"}]


def test_crear_solicitud_chat_success(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "insert_solicitud", lambda cursor, solicitud: 123)
    monkeypatch.setattr(routes.repository, "insert_solicitud_md", lambda cursor, id_solicitud, ruta: None)
    monkeypatch.setattr(routes, "render_solicitud_md", lambda *args, **kwargs: str(tmp_path / "123.md"))

    response = client.post(
        "/api/solicitudes/chat",
        data={
            "solicitante_email": "mesa.ayuda@dovela.com",
            "titulo": "Reporte de gastos",
            "descripcion": "Necesito un reporte de gastos personalizado.",
            "cliente": "Chantilly",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id_solicitud"] == 123
    assert body["cliente"] == "Chantilly"
    assert body["status_cd"] == "EN ESPERA"
    assert "Reporte de gastos" in body["titulo"]


def test_crear_solicitud_chat_invalid_email():
    response = client.post(
        "/api/solicitudes/chat",
        data={
            "solicitante_email": "no-es-un-correo",
            "titulo": "Reporte de gastos",
            "descripcion": "Necesito un reporte.",
        },
    )
    assert response.status_code == 422


def test_crear_solicitud_chat_rolls_back_on_db_error(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)

    def _boom(cursor, solicitud):
        raise RuntimeError("fallo simulado de BD")

    monkeypatch.setattr(routes.repository, "insert_solicitud", _boom)

    response = client.post(
        "/api/solicitudes/chat",
        data={
            "solicitante_email": "mesa.ayuda@dovela.com",
            "titulo": "Reporte de gastos",
            "descripcion": "Necesito un reporte.",
        },
    )

    assert response.status_code == 500
    assert fake_conn.rolled_back is True
    assert fake_conn.committed is False


def test_crear_solicitud_chat_con_adjuntos(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "insert_solicitud", lambda cursor, solicitud: 456)
    monkeypatch.setattr(routes.repository, "insert_solicitud_md", lambda cursor, id_solicitud, ruta: None)
    monkeypatch.setattr(routes, "render_solicitud_md", lambda *args, **kwargs: str(tmp_path / "456.md"))

    guardados = []
    monkeypatch.setattr(routes, "save_attachment", lambda id_solicitud, filename, content: (guardados.append(filename), f"/fake/{filename}")[1])

    adjuntos_insertados = []
    monkeypatch.setattr(
        routes.repository,
        "insert_adjunto",
        lambda cursor, id_solicitud, nombre_archivo, ruta, tipo_mime, tamano: adjuntos_insertados.append(nombre_archivo) or 1,
    )

    response = client.post(
        "/api/solicitudes/chat",
        data={
            "solicitante_email": "mesa.ayuda@dovela.com",
            "titulo": "Reporte de gastos",
            "descripcion": "Necesito un reporte con evidencia adjunta.",
        },
        files=[
            ("files", ("captura.png", b"contenido-fake-png", "image/png")),
            ("files", ("detalle.csv", b"col1,col2\n1,2\n", "text/csv")),
        ],
    )

    assert response.status_code == 201
    assert guardados == ["captura.png", "detalle.csv"]
    assert adjuntos_insertados == ["captura.png", "detalle.csv"]


def test_crear_solicitud_chat_rechaza_demasiados_adjuntos():
    archivos = [("files", (f"archivo{i}.txt", b"x", "text/plain")) for i in range(6)]

    response = client.post(
        "/api/solicitudes/chat",
        data={
            "solicitante_email": "mesa.ayuda@dovela.com",
            "titulo": "Reporte de gastos",
            "descripcion": "Necesito un reporte.",
        },
        files=archivos,
    )

    assert response.status_code == 422


def test_crear_solicitud_chat_rechaza_adjunto_muy_grande():
    contenido_grande = b"x" * (routes.MAX_ADJUNTO_SIZE_BYTES + 1)

    response = client.post(
        "/api/solicitudes/chat",
        data={
            "solicitante_email": "mesa.ayuda@dovela.com",
            "titulo": "Reporte de gastos",
            "descripcion": "Necesito un reporte.",
        },
        files=[("files", ("grande.bin", contenido_grande, "application/octet-stream"))],
    )

    assert response.status_code == 422


def test_listar_solicitudes(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())

    filtros_recibidos = {}

    def _fake_list_solicitudes(cursor, cliente=None, nombre=None, estatus=None):
        filtros_recibidos.update({"cliente": cliente, "nombre": nombre, "estatus": estatus})
        return [
            {
                "id": 1,
                "nombre": "Reporte de gastos",
                "cliente": "Chantilly",
                "tipo": "Nuevo",
                "codigo_estatus": "EN ESPERA",
                "estatus_descripcion": "En espera",
                "solicitante": "Ramon Rosales",
                "creado_en": datetime(2026, 8, 21, tzinfo=timezone.utc),
            }
        ]

    monkeypatch.setattr(routes.repository, "list_solicitudes", _fake_list_solicitudes)

    response = client.get("/api/solicitudes", params={"cliente": "chan", "estatus": "EN ESPERA"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["nombre"] == "Reporte de gastos"
    assert filtros_recibidos == {"cliente": "chan", "nombre": None, "estatus": "EN ESPERA"}


def test_crear_solicitud_formulario_success(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "insert_solicitud", lambda cursor, solicitud: 789)
    monkeypatch.setattr(routes.repository, "insert_solicitud_md", lambda cursor, id_solicitud, ruta: None)
    monkeypatch.setattr(routes, "render_solicitud_md", lambda *args, **kwargs: str(tmp_path / "789.md"))

    response = client.post(
        "/api/solicitudes/formulario",
        data={
            "solicitante_email": "ramon_rosales@stoconsulting.com",
            "titulo": "Nueva integración",
            "descripcion": "Detalle de la solicitud capturada por formulario.",
            "tipo": "Nuevo",
            "cliente": "Chantilly",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id_solicitud"] == 789
    assert body["cliente"] == "Chantilly"


def test_crear_solicitud_formulario_requiere_tipo():
    response = client.post(
        "/api/solicitudes/formulario",
        data={
            "solicitante_email": "ramon_rosales@stoconsulting.com",
            "titulo": "Nueva integración",
            "descripcion": "Detalle de la solicitud.",
        },
    )

    assert response.status_code == 422


def _fake_solicitud_detalle(solicitud_id=1):
    return {
        "id": solicitud_id,
        "nombre": "Reporte de gastos",
        "descripcion": "Detalle",
        "cliente": "Chantilly",
        "cliente_id": 10,
        "tipo": "Nuevo",
        "tipo_id": 3,
        "codigo_estatus": "EN ESPERA",
        "estatus_descripcion": "En espera",
        "solicitante": "Ramon Rosales",
        "orden_prioridad": None,
        "creado_en": datetime(2026, 8, 21, tzinfo=timezone.utc),
        "actualizado_en": datetime(2026, 8, 21, tzinfo=timezone.utc),
        "actualizado_por": "dovela_control",
    }


def test_obtener_solicitud_success(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))

    response = client.get("/api/solicitudes/1")

    assert response.status_code == 200
    assert response.json()["nombre"] == "Reporte de gastos"


def test_obtener_solicitud_404(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: None)

    response = client.get("/api/solicitudes/999")

    assert response.status_code == 404


def test_actualizar_solicitud_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "update_solicitud", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos actualizado",
            "descripcion": "Detalle actualizado",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "codigo_estatus": "EN PROCESO",
        },
    )

    assert response.status_code == 200
    assert fake_conn.committed is True


def test_actualizar_solicitud_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "update_solicitud", lambda cursor, id, **kwargs: 0)

    response = client.put(
        "/api/solicitudes/999",
        json={
            "nombre": "No existe",
            "descripcion": "Detalle",
            "cliente": None,
            "tipo": "Nuevo",
            "codigo_estatus": "EN PROCESO",
        },
    )

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_solicitud_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_solicitud", lambda cursor, id: 1)

    response = client.delete("/api/solicitudes/1")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_borrar_solicitud_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_solicitud", lambda cursor, id: 0)

    response = client.delete("/api/solicitudes/999")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def _fake_tarea(tarea_id=1, solicitud_id=1):
    return {
        "id": tarea_id,
        "solicitud_id": solicitud_id,
        "nombre": "Levantar requerimientos",
        "descripcion": "Reunión con el cliente",
        "responsable_id": 6,
        "responsable": "Ramon Rosales",
        "codigo_estatus_tarea": "POR HACER",
        "estatus_tarea_descripcion": "Por hacer",
        "fecha_inicio": date(2026, 8, 23),
        "fecha_fin": date(2026, 8, 30),
        "horas_estimadas": None,
        "horas_reales": None,
        "creado_en": datetime(2026, 8, 23, tzinfo=timezone.utc),
        "actualizado_en": datetime(2026, 8, 23, tzinfo=timezone.utc),
    }


def test_listar_tareas(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "list_tareas_by_solicitud", lambda cursor, id: [_fake_tarea()])

    response = client.get("/api/solicitudes/1/tareas")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_crear_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "insert_tarea", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    response = client.post(
        "/api/solicitudes/1/tareas",
        json={"nombre": "Levantar requerimientos", "descripcion": "Reunión con el cliente", "responsable_id": 6},
    )

    assert response.status_code == 201
    assert response.json()["nombre"] == "Levantar requerimientos"
    assert fake_conn.committed is True


def test_crear_tarea_pasa_fechas_y_horas_al_repositorio(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    kwargs_recibidos = {}

    def _fake_insert_tarea(cursor, id, **kwargs):
        kwargs_recibidos.update(kwargs)
        return 1

    monkeypatch.setattr(routes.repository, "insert_tarea", _fake_insert_tarea)

    response = client.post(
        "/api/solicitudes/1/tareas",
        json={
            "nombre": "Levantar requerimientos",
            "descripcion": "Reunión con el cliente",
            "responsable_id": 6,
            "fecha_inicio": "2026-08-24",
            "fecha_fin": "2026-08-28",
            "horas_estimadas": 8,
            "horas_reales": 5,
        },
    )

    assert response.status_code == 201
    assert kwargs_recibidos["fecha_inicio"] == date(2026, 8, 24)
    assert kwargs_recibidos["fecha_fin"] == date(2026, 8, 28)
    assert kwargs_recibidos["horas_estimadas"] == 8
    assert kwargs_recibidos["horas_reales"] == 5

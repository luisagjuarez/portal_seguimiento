from datetime import date, datetime, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user, require_scrum_master
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
    monkeypatch.setattr(routes.repository, "insert_solicitud", lambda cursor, solicitud, **kwargs: 123)
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
    monkeypatch.setattr(routes.repository, "insert_solicitud", lambda cursor, solicitud, **kwargs: 456)
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

    def _fake_list_solicitudes(
        cursor, cliente=None, nombre=None, estatus=None, area=None, orden_por=None, involucrado_id=None
    ):
        filtros_recibidos.update(
            {"cliente": cliente, "nombre": nombre, "estatus": estatus, "orden_por": orden_por}
        )
        return [
            {
                "id": 1,
                "nombre": "Reporte de gastos",
                "cliente": "Chantilly",
                "tipo": "Nuevo",
                "codigo_estatus": "EN ESPERA",
                "estatus_descripcion": "En espera",
                "solicitante": "Ramon Rosales",
                "orden_prioridad": 3,
                "fecha_entrega": None,
                "responsable_atencion": None,
                "responsable_atencion_area": "Sin área",
                "creado_en": datetime(2026, 8, 21, tzinfo=timezone.utc),
            }
        ]

    monkeypatch.setattr(routes.repository, "list_solicitudes", _fake_list_solicitudes)

    response = client.get("/api/solicitudes", params={"cliente": "chan", "estatus": "EN ESPERA"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["nombre"] == "Reporte de gastos"
    assert filtros_recibidos == {
        "cliente": "chan",
        "nombre": None,
        "estatus": "EN ESPERA",
        "orden_por": None,
    }


def test_listar_solicitudes_ordenadas(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())

    filtros_recibidos = {}

    def _fake_list_solicitudes(
        cursor, cliente=None, nombre=None, estatus=None, area=None, orden_por=None, involucrado_id=None
    ):
        filtros_recibidos.update({"orden_por": orden_por})
        return []

    monkeypatch.setattr(routes.repository, "list_solicitudes", _fake_list_solicitudes)

    response = client.get("/api/solicitudes", params={"orden_por": "prioridad"})

    assert response.status_code == 200
    assert filtros_recibidos == {"orden_por": "prioridad"}


def test_listar_solicitudes_filtra_por_involucrado(monkeypatch):
    """Fase 1.19: el filtro 'mis solicitudes' se traduce en involucrado_id hacia el repository."""
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())

    filtros_recibidos = {}

    def _fake_list_solicitudes(
        cursor, cliente=None, nombre=None, estatus=None, area=None, orden_por=None, involucrado_id=None
    ):
        filtros_recibidos.update({"involucrado_id": involucrado_id})
        return []

    monkeypatch.setattr(routes.repository, "list_solicitudes", _fake_list_solicitudes)

    response = client.get("/api/solicitudes", params={"involucrado_id": 6})

    assert response.status_code == 200
    assert filtros_recibidos == {"involucrado_id": 6}


def test_listar_solicitudes_filtra_por_area(monkeypatch):
    """Punto 3 (2026-09-04): filtro por área (perfil) del responsable de atención."""
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())

    filtros_recibidos = {}

    def _fake_list_solicitudes(
        cursor, cliente=None, nombre=None, estatus=None, area=None, orden_por=None, involucrado_id=None
    ):
        filtros_recibidos.update({"area": area})
        return []

    monkeypatch.setattr(routes.repository, "list_solicitudes", _fake_list_solicitudes)

    response = client.get("/api/solicitudes", params={"area": "Infraestructura"})

    assert response.status_code == 200
    assert filtros_recibidos == {"area": "Infraestructura"}


def test_crear_solicitud_formulario_success(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "insert_solicitud", lambda cursor, solicitud, **kwargs: 789)
    monkeypatch.setattr(routes.repository, "insert_solicitud_md", lambda cursor, id_solicitud, ruta: None)
    monkeypatch.setattr(routes, "render_solicitud_md", lambda *args, **kwargs: str(tmp_path / "789.md"))

    response = client.post(
        "/api/solicitudes/formulario",
        data={
            "solicitante_email": "ramon_rosales@stoconsulting.com",
            "titulo": "Nueva integración",
            "descripcion": "Detalle de la solicitud capturada por formulario.",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "orden_prioridad": "2",
            "cliente": "Chantilly",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id_solicitud"] == 789
    assert body["cliente"] == "Chantilly"


def test_crear_solicitud_formulario_orden_prioridad_default(monkeypatch, tmp_path):
    """Fase 1.17: si no se manda orden_prioridad, debe quedar en 3 (Media) por default."""
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)

    solicitudes_creadas = {}

    def _fake_insert_solicitud(cursor, solicitud, **kwargs):
        solicitudes_creadas["orden_prioridad"] = solicitud.orden_prioridad
        return 789

    monkeypatch.setattr(routes.repository, "insert_solicitud", _fake_insert_solicitud)
    monkeypatch.setattr(routes.repository, "insert_solicitud_md", lambda cursor, id_solicitud, ruta: None)
    monkeypatch.setattr(routes, "render_solicitud_md", lambda *args, **kwargs: str(tmp_path / "789.md"))

    response = client.post(
        "/api/solicitudes/formulario",
        data={
            "solicitante_email": "ramon_rosales@stoconsulting.com",
            "titulo": "Nueva integración",
            "descripcion": "Detalle de la solicitud capturada por formulario.",
            "tipo": "Nuevo",
            "canal": "Formulario",
        },
    )

    assert response.status_code == 201
    assert solicitudes_creadas["orden_prioridad"] == 3


def test_crear_solicitud_formulario_pasa_sr_ebs(monkeypatch, tmp_path):
    """Punto 5 (2026-09-04): sr_ebs es opcional, y si se manda viaja hasta insert_solicitud."""
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)

    solicitudes_creadas = {}

    def _fake_insert_solicitud(cursor, solicitud, **kwargs):
        solicitudes_creadas["sr_ebs"] = solicitud.sr_ebs
        return 789

    monkeypatch.setattr(routes.repository, "insert_solicitud", _fake_insert_solicitud)
    monkeypatch.setattr(routes.repository, "insert_solicitud_md", lambda cursor, id_solicitud, ruta: None)
    monkeypatch.setattr(routes, "render_solicitud_md", lambda *args, **kwargs: str(tmp_path / "789.md"))

    response = client.post(
        "/api/solicitudes/formulario",
        data={
            "solicitante_email": "ramon_rosales@stoconsulting.com",
            "titulo": "Nueva integración",
            "descripcion": "Detalle de la solicitud capturada por formulario.",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "sr_ebs": "SR-12345",
        },
    )

    assert response.status_code == 201
    assert solicitudes_creadas["sr_ebs"] == "SR-12345"


def test_crear_solicitud_formulario_sin_sr_ebs_no_es_obligatorio(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)

    solicitudes_creadas = {}

    def _fake_insert_solicitud(cursor, solicitud, **kwargs):
        solicitudes_creadas["sr_ebs"] = solicitud.sr_ebs
        return 789

    monkeypatch.setattr(routes.repository, "insert_solicitud", _fake_insert_solicitud)
    monkeypatch.setattr(routes.repository, "insert_solicitud_md", lambda cursor, id_solicitud, ruta: None)
    monkeypatch.setattr(routes, "render_solicitud_md", lambda *args, **kwargs: str(tmp_path / "789.md"))

    response = client.post(
        "/api/solicitudes/formulario",
        data={
            "solicitante_email": "ramon_rosales@stoconsulting.com",
            "titulo": "Nueva integración",
            "descripcion": "Detalle de la solicitud capturada por formulario.",
            "tipo": "Nuevo",
            "canal": "Formulario",
        },
    )

    assert response.status_code == 201
    assert solicitudes_creadas["sr_ebs"] is None


def test_actualizar_solicitud_pasa_sr_ebs_al_repositorio(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "find_canal_id_by_name", lambda cursor, canal: 3)
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))

    kwargs_recibidos = {}

    def _fake_update_solicitud(cursor, id, **kwargs):
        kwargs_recibidos.update(kwargs)
        return 1

    monkeypatch.setattr(routes.repository, "update_solicitud", _fake_update_solicitud)

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "EN ESPERA",
            "sr_ebs": "SR-99999",
        },
    )

    assert response.status_code == 200
    assert kwargs_recibidos["sr_ebs"] == "SR-99999"


def test_crear_solicitud_formulario_rechaza_prioridad_fuera_de_rango():
    for valor in ("0", "6", "alta"):
        response = client.post(
            "/api/solicitudes/formulario",
            data={
                "solicitante_email": "ramon_rosales@stoconsulting.com",
                "titulo": "Nueva integración",
                "descripcion": "Detalle de la solicitud.",
                "tipo": "Nuevo",
                "canal": "Formulario",
                "orden_prioridad": valor,
            },
        )
        assert response.status_code == 422, f"orden_prioridad={valor!r} debería rechazarse"


def test_actualizar_solicitud_rechaza_prioridad_fuera_de_rango(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "orden_prioridad": 6,
            "codigo_estatus": "EN ESPERA",
        },
    )

    assert response.status_code == 422


def test_crear_solicitud_formulario_requiere_tipo():
    response = client.post(
        "/api/solicitudes/formulario",
        data={
            "solicitante_email": "ramon_rosales@stoconsulting.com",
            "titulo": "Nueva integración",
            "descripcion": "Detalle de la solicitud.",
            "canal": "Formulario",
        },
    )

    assert response.status_code == 422


def test_crear_solicitud_formulario_requiere_canal():
    response = client.post(
        "/api/solicitudes/formulario",
        data={
            "solicitante_email": "ramon_rosales@stoconsulting.com",
            "titulo": "Nueva integración",
            "descripcion": "Detalle de la solicitud.",
            "tipo": "Nuevo",
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
        "solicitante_id": 1,
        "orden_prioridad": 3,
        "canal": "Formulario",
        "canal_id": 3,
        "fecha_completado": None,
        "fecha_entrega": None,
        "responsable_atencion_id": None,
        "responsable_atencion": None,
        "responsable_atencion_area": "Sin área",
        "sr_ebs": None,
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
    monkeypatch.setattr(routes.repository, "find_canal_id_by_name", lambda cursor, canal: 3)
    monkeypatch.setattr(routes.repository, "update_solicitud", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos actualizado",
            "descripcion": "Detalle actualizado",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "orden_prioridad": 1,
            "codigo_estatus": "EN PROCESO",
        },
    )

    assert response.status_code == 200
    assert fake_conn.committed is True


def test_actualizar_solicitud_422_si_responsable_atencion_es_externo(monkeypatch):
    """Punto 1 (2026-09-04): un Externo no puede ser responsable de atención de una solicitud."""
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "es_miembro_externo", lambda cursor, id: id == 10)

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "PLANEADO",
            "fecha_entrega": "2026-09-15",
            "responsable_atencion_id": 10,
        },
    )

    assert response.status_code == 422


def test_actualizar_solicitud_planeado_requiere_fecha_entrega_y_responsable():
    """Fase 1.18: al pasar a Planeado (o posterior), fecha_entrega y responsable_atencion_id
    son obligatorios."""
    for estatus in ("PLANEADO", "EN PROGRESO", "COMPLETADO"):
        response = client.put(
            "/api/solicitudes/1",
            json={
                "nombre": "Reporte de gastos",
                "descripcion": "Detalle",
                "cliente": "Chantilly",
                "tipo": "Nuevo",
                "canal": "Formulario",
                "codigo_estatus": estatus,
                "fecha_completado": "2026-08-24" if estatus == "COMPLETADO" else None,
            },
        )
        assert response.status_code == 422, f"estatus={estatus} debería exigir fecha_entrega/responsable"


def test_actualizar_solicitud_planeado_con_fecha_entrega_y_responsable_ok(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "find_canal_id_by_name", lambda cursor, canal: 3)
    monkeypatch.setattr(routes.repository, "update_solicitud", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "insert_notificacion", lambda cursor, *args, **kwargs: 1)

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "PLANEADO",
            "fecha_entrega": "2026-09-15",
            "responsable_atencion_id": 6,
        },
    )

    assert response.status_code == 200
    assert fake_conn.committed is True


def test_actualizar_solicitud_notifica_al_asignar_responsable_atencion(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "find_canal_id_by_name", lambda cursor, canal: 3)
    monkeypatch.setattr(routes.repository, "update_solicitud", lambda cursor, id, **kwargs: 1)
    # _fake_solicitud_detalle trae responsable_atencion_id=None -> el body lo cambia a 6
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append((destinatario_id, kwargs["tipo"])),
    )

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "PLANEADO",
            "fecha_entrega": "2026-09-15",
            "responsable_atencion_id": 6,
        },
    )

    assert response.status_code == 200
    assert notificaciones == [(6, "SOLICITUD_ASIGNADA")]


def test_actualizar_solicitud_notifica_aunque_se_asigne_a_si_mismo(monkeypatch):
    """Ajuste: ya no se excluye la auto-notificación al asignarse uno mismo como responsable
    de atención (USUARIO_DE_PRUEBA de conftest tiene id=1)."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "find_canal_id_by_name", lambda cursor, canal: 3)
    monkeypatch.setattr(routes.repository, "update_solicitud", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append((destinatario_id, kwargs["tipo"])),
    )

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "PLANEADO",
            "fecha_entrega": "2026-09-15",
            "responsable_atencion_id": 1,
        },
    )

    assert response.status_code == 200
    assert notificaciones == [(1, "SOLICITUD_ASIGNADA")]


def test_actualizar_solicitud_en_espera_no_requiere_fecha_entrega(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "find_canal_id_by_name", lambda cursor, canal: 3)
    monkeypatch.setattr(routes.repository, "update_solicitud", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": "Chantilly",
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "EN ESPERA",
        },
    )

    assert response.status_code == 200


def test_actualizar_solicitud_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "find_canal_id_by_name", lambda cursor, canal: 3)
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: None)
    monkeypatch.setattr(routes.repository, "update_solicitud", lambda cursor, id, **kwargs: 0)

    response = client.put(
        "/api/solicitudes/999",
        json={
            "nombre": "No existe",
            "descripcion": "Detalle",
            "cliente": None,
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "EN PROCESO",
        },
    )

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_actualizar_solicitud_completado_requiere_fecha():
    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": None,
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "COMPLETADO",
        },
    )

    assert response.status_code == 422


def test_actualizar_solicitud_completado_con_fecha(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_or_create_cliente", lambda cursor, nombre: nombre)
    monkeypatch.setattr(routes.repository, "find_cliente_id_by_name", lambda cursor, nombre: 10)
    monkeypatch.setattr(routes.repository, "find_tipo_id", lambda cursor, tipo: 3)
    monkeypatch.setattr(routes.repository, "find_canal_id_by_name", lambda cursor, canal: 3)

    kwargs_recibidos = {}

    def _fake_update_solicitud(cursor, id, **kwargs):
        kwargs_recibidos.update(kwargs)
        return 1

    monkeypatch.setattr(routes.repository, "update_solicitud", _fake_update_solicitud)
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "insert_notificacion", lambda cursor, *args, **kwargs: 1)

    response = client.put(
        "/api/solicitudes/1",
        json={
            "nombre": "Reporte de gastos",
            "descripcion": "Detalle",
            "cliente": None,
            "tipo": "Nuevo",
            "canal": "Formulario",
            "codigo_estatus": "COMPLETADO",
            "fecha_completado": "2026-08-24",
            "fecha_entrega": "2026-08-20",
            "responsable_atencion_id": 6,
        },
    )

    assert response.status_code == 200
    assert kwargs_recibidos["fecha_completado"] == date(2026, 8, 24)


def test_borrar_solicitud_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_solicitud", lambda cursor, id, **kwargs: 1)

    response = client.delete("/api/solicitudes/1")

    assert response.status_code == 204
    assert fake_conn.committed is True


def test_borrar_solicitud_404(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "delete_solicitud", lambda cursor, id, **kwargs: 0)

    response = client.delete("/api/solicitudes/999")

    assert response.status_code == 404
    assert fake_conn.rolled_back is True


def test_borrar_solicitud_403_si_no_es_scrum_master():
    def _denegar_scrum_master():
        raise HTTPException(status_code=403, detail="Solo el Scrum Master puede hacer esto")

    app.dependency_overrides[require_scrum_master] = _denegar_scrum_master
    try:
        response = client.delete("/api/solicitudes/1")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[require_scrum_master]


def _fake_tarea(tarea_id=1, solicitud_id=1):
    return {
        "id": tarea_id,
        "solicitud_id": solicitud_id,
        "nombre": "Levantar requerimientos",
        "descripcion": "Reunión con el cliente",
        "responsable_id": 6,
        "responsable": "Ramon Rosales",
        "solicitud_prioridad": 3,
        "solicitud_fecha_entrega": None,
        "solicitud_codigo_estatus": "EN PROGRESO",
        "codigo_estatus_tarea": "POR HACER",
        "estatus_tarea_descripcion": "Por hacer",
        "fecha_inicio": date(2026, 8, 23),
        "fecha_fin": date(2026, 8, 30),
        "fecha_inicio_real": None,
        "fecha_fin_real": None,
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
    assert response.json()[0]["solicitud_prioridad"] == 3


def test_listar_comentarios_solicitud(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    fake_comentario = {
        "id": 1,
        "solicitud_id": 1,
        "tarea_id": 1,
        "tarea_nombre": "Levantar requerimientos",
        "texto_comentario": "Quedamos en revisar esto el viernes.",
        "creado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "creado_por": "DOVELA_LG",
        "creado_por_nombre": "Luis Gómez",
        "actualizado_en": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "actualizado_por": "DOVELA_LG",
    }
    monkeypatch.setattr(routes.repository, "list_comentarios_by_solicitud", lambda cursor, id: [fake_comentario])

    response = client.get("/api/solicitudes/1/comentarios")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["creado_por_nombre"] == "Luis Gómez"


def test_listar_hitos_solicitud(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    fake_hito = {
        "id": 1,
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
    monkeypatch.setattr(routes.repository, "list_hitos_by_solicitud", lambda cursor, id: [fake_hito])

    response = client.get("/api/solicitudes/1/hitos")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["creado_por_nombre"] == "Luis Gómez"


def test_listar_enlaces_solicitud(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    fake_enlace = {
        "id": 1,
        "solicitud_id": 1,
        "tarea_id": 1,
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
    monkeypatch.setattr(routes.repository, "list_enlaces_by_solicitud", lambda cursor, id: [fake_enlace])

    response = client.get("/api/solicitudes/1/enlaces")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["creado_por_nombre"] == "Luis Gómez"


def test_listar_adjuntos_solicitud(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    fake_adjunto = {
        "id": 1,
        "nombre_archivo": "captura.png",
        "tipo_mime": "image/png",
        "tamano_bytes": 1234,
        "fecha_carga": datetime(2026, 8, 24, tzinfo=timezone.utc),
    }
    monkeypatch.setattr(routes.repository, "list_adjuntos_by_solicitud", lambda cursor, id: [fake_adjunto])

    response = client.get("/api/solicitudes/1/adjuntos")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["nombre_archivo"] == "captura.png"


def test_descargar_adjunto_solicitud_success(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))

    archivo = tmp_path / "captura.png"
    archivo.write_bytes(b"contenido-fake-png")

    monkeypatch.setattr(
        routes.repository,
        "get_adjunto_de_solicitud",
        lambda cursor, solicitud_id, adjunto_id: {
            "id": adjunto_id,
            "nombre_archivo": "captura.png",
            "ruta_almacenamiento": str(archivo),
            "tipo_mime": "image/png",
            "tamano_bytes": 19,
        },
    )

    response = client.get("/api/solicitudes/1/adjuntos/1/descargar")

    assert response.status_code == 200
    assert response.content == b"contenido-fake-png"
    assert response.headers["content-type"] == "image/png"


def test_descargar_adjunto_solicitud_404_si_no_pertenece(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(
        routes.repository, "get_adjunto_de_solicitud", lambda cursor, solicitud_id, adjunto_id: None
    )

    response = client.get("/api/solicitudes/1/adjuntos/999/descargar")

    assert response.status_code == 404


def test_descargar_adjunto_solicitud_404_si_falta_en_disco(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    ruta_inexistente = str(tmp_path / "no-existe.png")
    monkeypatch.setattr(
        routes.repository,
        "get_adjunto_de_solicitud",
        lambda cursor, solicitud_id, adjunto_id: {
            "id": adjunto_id,
            "nombre_archivo": "no-existe.png",
            "ruta_almacenamiento": ruta_inexistente,
            "tipo_mime": "image/png",
            "tamano_bytes": 10,
        },
    )

    response = client.get("/api/solicitudes/1/adjuntos/1/descargar")

    assert response.status_code == 404


def test_agregar_adjuntos_solicitud_success(monkeypatch, tmp_path):
    """Fase 1.21: agregar adjuntos a una solicitud ya creada (antes solo se podía al crearla)."""
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "count_adjuntos_by_solicitud", lambda cursor, id: 2)
    monkeypatch.setattr(routes, "save_attachment", lambda id_solicitud, filename, content: f"/fake/{filename}")

    guardados = []

    def _fake_insert_adjunto(cursor, id_solicitud, nombre_archivo, ruta, tipo_mime, tamano):
        guardados.append(nombre_archivo)
        return len(guardados)

    monkeypatch.setattr(routes.repository, "insert_adjunto", _fake_insert_adjunto)
    monkeypatch.setattr(
        routes.repository,
        "list_adjuntos_by_solicitud",
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

    response = client.post(
        "/api/solicitudes/1/adjuntos", files=[("files", ("nuevo.txt", b"contenido", "text/plain"))]
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["nombre_archivo"] == "nuevo.txt"


def test_agregar_adjuntos_solicitud_rechaza_si_pasa_del_maximo(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    # ya tiene 5 adjuntos -> 0 disponibles, cualquier archivo nuevo se rechaza
    monkeypatch.setattr(routes.repository, "count_adjuntos_by_solicitud", lambda cursor, id: 5)

    response = client.post(
        "/api/solicitudes/1/adjuntos", files=[("files", ("otro.txt", b"contenido", "text/plain"))]
    )

    assert response.status_code == 422


def test_agregar_adjuntos_solicitud_404_si_no_existe(monkeypatch):
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: None)

    response = client.post(
        "/api/solicitudes/999/adjuntos", files=[("files", ("nuevo.txt", b"contenido", "text/plain"))]
    )

    assert response.status_code == 404


def test_crear_tarea_success(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "insert_tarea", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_notificacion", lambda cursor, *args, **kwargs: 1)

    response = client.post(
        "/api/solicitudes/1/tareas",
        json={"nombre": "Levantar requerimientos", "descripcion": "Reunión con el cliente", "responsable_id": 6},
    )

    assert response.status_code == 201
    assert response.json()["nombre"] == "Levantar requerimientos"
    assert fake_conn.committed is True


def test_crear_tarea_422_si_responsable_es_externo(monkeypatch):
    """Punto 1 (2026-09-04): un Externo no puede ser responsable de una tarea."""
    monkeypatch.setattr(routes, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "es_miembro_externo", lambda cursor, id: id == 10)

    response = client.post(
        "/api/solicitudes/1/tareas",
        json={"nombre": "Levantar requerimientos", "responsable_id": 10},
    )

    assert response.status_code == 422


def test_crear_tarea_marca_solicitud_en_progreso_si_nace_en_progreso(monkeypatch):
    """Punto 4 (2026-09-04): si la tarea nace directamente en "En progreso", también dispara
    el intento de pasar la solicitud a "En progreso" (la guarda de "seguía en Planeado" vive en
    el UPDATE de marcar_solicitud_en_progreso, no aquí)."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "insert_tarea", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    llamadas = []
    monkeypatch.setattr(
        routes.repository,
        "marcar_solicitud_en_progreso",
        lambda cursor, solicitud_id, actor: llamadas.append(solicitud_id),
    )

    response = client.post(
        "/api/solicitudes/1/tareas",
        json={"nombre": "Levantar requerimientos", "codigo_estatus_tarea": "EN PROGRESO"},
    )

    assert response.status_code == 201
    assert llamadas == [1]


def test_crear_tarea_no_marca_solicitud_si_nace_por_hacer(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "insert_tarea", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    llamadas = []
    monkeypatch.setattr(
        routes.repository,
        "marcar_solicitud_en_progreso",
        lambda cursor, solicitud_id, actor: llamadas.append(solicitud_id),
    )

    response = client.post(
        "/api/solicitudes/1/tareas",
        json={"nombre": "Levantar requerimientos", "codigo_estatus_tarea": "POR HACER"},
    )

    assert response.status_code == 201
    assert llamadas == []


def test_crear_tarea_notifica_al_responsable(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "insert_tarea", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append((destinatario_id, kwargs["tipo"])),
    )

    response = client.post(
        "/api/solicitudes/1/tareas",
        json={"nombre": "Levantar requerimientos", "descripcion": "Reunión", "responsable_id": 6},
    )

    assert response.status_code == 201
    assert notificaciones == [(6, "TAREA_ASIGNADA")]


def test_crear_tarea_notifica_aunque_el_responsable_sea_quien_crea(monkeypatch):
    """El responsable de atención (o el Scrum Master) puede asignarse la tarea a sí mismo y
    aun así recibir la notificación (ajuste: ya no se excluye la auto-notificación)."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "insert_tarea", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))

    notificaciones = []
    monkeypatch.setattr(
        routes.repository,
        "insert_notificacion",
        lambda cursor, destinatario_id, **kwargs: notificaciones.append((destinatario_id, kwargs["tipo"])),
    )

    # USUARIO_DE_PRUEBA (conftest) tiene id=1
    response = client.post(
        "/api/solicitudes/1/tareas",
        json={"nombre": "Levantar requerimientos", "descripcion": "Reunión", "responsable_id": 1},
    )

    assert response.status_code == 201
    assert notificaciones == [(1, "TAREA_ASIGNADA")]


def test_crear_tarea_403_si_no_es_scrum_master_ni_responsable_de_atencion(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    solicitud = _fake_solicitud_detalle(1)
    solicitud["responsable_atencion_id"] = 99
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: solicitud)

    otro_usuario = UsuarioActual(
        id=2,
        usuario="DOVELA_WA",
        nombre_completo="Wendy Aguilar",
        codigo_rol_scrum="TEAM",
        correo_electronico="wendy@dovela.com",
        debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: otro_usuario
    try:
        response = client.post("/api/solicitudes/1/tareas", json={"nombre": "Levantar requerimientos"})
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


def test_crear_tarea_permitido_al_responsable_de_atencion_aunque_no_sea_scrum_master(monkeypatch):
    """Fase 1.18 + ajuste: cualquier miembro (Product Owner, Scrum Master o Team) asignado
    como responsable de atención de la solicitud puede crear y asignar tareas dentro de ella."""
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    solicitud = _fake_solicitud_detalle(1)
    solicitud["responsable_atencion_id"] = 2
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: solicitud)
    monkeypatch.setattr(routes.repository, "insert_tarea", lambda cursor, id, **kwargs: 1)
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_notificacion", lambda cursor, *args, **kwargs: 1)

    product_owner = UsuarioActual(
        id=2,
        usuario="DOVELA_JC",
        nombre_completo="Juan Carlos",
        codigo_rol_scrum="PRODUCT OWNER",
        correo_electronico="juan.carlos@dovela.com",
        debe_cambiar_password=False,
    )
    app.dependency_overrides[get_current_user] = lambda: product_owner
    try:
        response = client.post(
            "/api/solicitudes/1/tareas",
            json={"nombre": "Levantar requerimientos", "responsable_id": 6},
        )
        assert response.status_code == 201
    finally:
        del app.dependency_overrides[get_current_user]


def test_crear_tarea_404_si_la_solicitud_no_existe(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: None)

    response = client.post("/api/solicitudes/999/tareas", json={"nombre": "Levantar requerimientos"})

    assert response.status_code == 404


def test_crear_tarea_pasa_fechas_y_horas_al_repositorio(monkeypatch):
    fake_conn = _FakeConnection()
    monkeypatch.setattr(routes, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(routes, "release_connection", lambda conn: conn.close())
    monkeypatch.setattr(routes.repository, "get_solicitud_by_id", lambda cursor, id: _fake_solicitud_detalle(id))
    monkeypatch.setattr(routes.repository, "get_tarea_by_id", lambda cursor, id: _fake_tarea(id))
    monkeypatch.setattr(routes.repository, "insert_notificacion", lambda cursor, *args, **kwargs: 1)

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
            "fecha_inicio_real": "2026-08-25",
            "fecha_fin_real": "2026-08-29",
            "horas_estimadas": 8,
            "horas_reales": 5,
        },
    )

    assert response.status_code == 201
    assert kwargs_recibidos["fecha_inicio"] == date(2026, 8, 24)
    assert kwargs_recibidos["fecha_fin"] == date(2026, 8, 28)
    assert kwargs_recibidos["fecha_inicio_real"] == date(2026, 8, 25)
    assert kwargs_recibidos["fecha_fin_real"] == date(2026, 8, 29)
    assert kwargs_recibidos["horas_estimadas"] == 8
    assert kwargs_recibidos["horas_reales"] == 5

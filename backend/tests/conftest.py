import pytest

from app.api.app import app
from app.auth.dependencies import UsuarioActual, get_current_user, require_scrum_master
from app.db import repository

USUARIO_DE_PRUEBA = UsuarioActual(
    id=1,
    usuario="DOVELA_LG",
    nombre_completo="Luis Gómez",
    codigo_rol_scrum="SCRUM MASTER",
    correo_electronico="luis.gomez@dovela.com",
    debe_cambiar_password=False,
)


@pytest.fixture(autouse=True)
def usuario_autenticado_de_prueba():
    """La mayoría de los endpoints ahora exigen sesión — por default los tests corren como
    un Scrum Master autenticado (pasa tanto get_current_user como require_scrum_master), así
    los tests existentes no necesitan simular login uno por uno. Los tests que sí quieran
    verificar el 401 (sin sesión) o el 403 (rol distinto de Scrum Master) sobrescriben estos
    overrides puntualmente."""
    app.dependency_overrides[get_current_user] = lambda: USUARIO_DE_PRUEBA
    app.dependency_overrides[require_scrum_master] = lambda: USUARIO_DE_PRUEBA
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_scrum_master, None)


@pytest.fixture(autouse=True)
def nadie_es_externo_por_default(monkeypatch):
    """Punto 1 (2026-09-04): la mayoría de los tests que asignan un responsable_id/
    responsable_atencion_id no están probando la regla "un Externo no puede ser responsable" —
    por default nadie es Externo, así no hace falta mockear `es_miembro_externo` uno por uno.
    Los tests que sí prueban esa regla lo sobrescriben puntualmente con `monkeypatch`."""
    monkeypatch.setattr(repository, "es_miembro_externo", lambda cursor, miembro_id: False)

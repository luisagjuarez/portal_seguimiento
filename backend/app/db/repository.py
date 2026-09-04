from __future__ import annotations

import logging
from datetime import date, timedelta

from app.models import NuevaSolicitud

logger = logging.getLogger(__name__)

_CANAL_POR_ORIGEN = {
    "EMAIL": "Correo",
    "CHAT": "Chatbot",
    "FORMULARIO": "Formulario",
}


def find_cliente_by_name(cursor, nombre: str) -> str | None:
    cursor.execute("SELECT nombre FROM clientes WHERE nombre ILIKE %(nombre)s", {"nombre": nombre})
    row = cursor.fetchone()
    return row[0] if row else None


def list_cliente_names(cursor) -> list[str]:
    cursor.execute("SELECT nombre FROM clientes WHERE nombre IS NOT NULL")
    return [row[0] for row in cursor.fetchall()]


def search_cliente_names(cursor, texto: str, limit: int = 10) -> list[str]:
    """Usado por el autocompletar del wizard de chat (GET /api/clientes?q=)."""
    cursor.execute(
        """
        SELECT nombre FROM clientes
        WHERE nombre IS NOT NULL AND nombre ILIKE %(patron)s
        ORDER BY nombre
        LIMIT %(max_rows)s
        """,
        {"patron": f"%{texto}%", "max_rows": limit},
    )
    return [row[0] for row in cursor.fetchall()]


def get_or_create_cliente(cursor, nombre_candidato: str | None) -> str | None:
    """clientes no tiene UNIQUE en nombre: la búsqueda de existencia es por texto
    (case-insensitive). Retorna el nombre tal como debe mostrarse (en el .md y en la
    respuesta de la API); insert_solicitud resuelve el id por separado."""
    if not nombre_candidato:
        return None
    existente = find_cliente_by_name(cursor, nombre_candidato)
    if existente:
        return existente
    cursor.execute("INSERT INTO clientes (nombre) VALUES (%(nombre)s)", {"nombre": nombre_candidato})
    return nombre_candidato


def find_cliente_id_by_name(cursor, nombre: str) -> int | None:
    cursor.execute("SELECT id FROM clientes WHERE nombre ILIKE %(nombre)s", {"nombre": nombre})
    row = cursor.fetchone()
    return row[0] if row else None


def find_miembro_id_by_email(cursor, email: str | None) -> int | None:
    """El solicitante siempre es un miembro del equipo DOVELA (nunca el cliente externo):
    se identifica por el email de quien mandó el correo o llenó el chat. Si no hay match,
    queda NULL para revisión manual, igual que se hace hoy con el cliente no identificado."""
    if not email:
        return None
    cursor.execute(
        "SELECT id FROM miembros_equipo WHERE correo_electronico ILIKE %(email)s",
        {"email": email},
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    logger.warning("No se encontró miembro del equipo con email=%s; solicitante queda NULL", email)
    return None


def find_canal_id(cursor, canal_origen: str) -> int | None:
    nombre_canal = _CANAL_POR_ORIGEN.get(canal_origen)
    if not nombre_canal:
        return None
    cursor.execute("SELECT id FROM canales_solicitud WHERE canal ILIKE %(nombre)s", {"nombre": nombre_canal})
    row = cursor.fetchone()
    return row[0] if row else None


def find_tipo_id(cursor, tipo: str | None) -> int | None:
    if not tipo:
        return None
    cursor.execute("SELECT id FROM tipos_solicitud WHERE tipo ILIKE %(tipo)s", {"tipo": tipo})
    row = cursor.fetchone()
    return row[0] if row else None


def find_canal_id_by_name(cursor, canal: str | None) -> int | None:
    """A diferencia de find_canal_id (que resuelve a partir del código interno de origen
    EMAIL/CHAT/FORMULARIO), esta resuelve directo por el nombre de catálogo que elige el
    usuario en el <select> de canal del formulario de Solicitudes."""
    if not canal:
        return None
    cursor.execute("SELECT id FROM canales_solicitud WHERE canal ILIKE %(canal)s", {"canal": canal})
    row = cursor.fetchone()
    return row[0] if row else None


def list_canales_solicitud(cursor) -> list[dict]:
    cursor.execute("SELECT id, canal FROM canales_solicitud ORDER BY id")
    return [{"id": row[0], "canal": row[1]} for row in cursor.fetchall()]


def is_message_processed(cursor, message_id: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM emails_procesados WHERE email_message_id = %(message_id)s",
        {"message_id": message_id},
    )
    return cursor.fetchone() is not None


def insert_solicitud(cursor, solicitud: NuevaSolicitud, actor: str = "PUBLICO") -> int:
    """Inserta en solicitudes. A diferencia del diseño anterior (acoplado a Oracle/APEX,
    con un trigger que llenaba auditoría e ID), este esquema no tiene triggers ni column
    defaults: hay que llenar creado_en/creado_por/actualizado_en/actualizado_por a mano, y
    resolver cliente/tipo/canal/solicitante (FKs numéricas) a partir de los valores de texto
    que trae NuevaSolicitud. `actor` es quien queda como creado_por/actualizado_por: el
    `usuario` del portal autenticado, o "PUBLICO" para los canales sin login (chat/correo),
    que siguen abiertos a clientes externos."""
    solicitante_id = find_miembro_id_by_email(cursor, solicitud.solicitante_email)
    cliente_id = find_cliente_id_by_name(cursor, solicitud.cliente) if solicitud.cliente else None
    tipo_id = find_tipo_id(cursor, solicitud.tipo)
    canal_id = (
        find_canal_id_by_name(cursor, solicitud.canal_nombre)
        if solicitud.canal_nombre
        else find_canal_id(cursor, solicitud.canal_origen)
    )

    cursor.execute(
        """
        INSERT INTO solicitudes
            (nombre, descripcion, solicitante, cliente, tipo, codigo_estatus, canal,
             orden_prioridad, sr_ebs, creado_en, creado_por, actualizado_en, actualizado_por)
        VALUES
            (%(nombre)s, %(descripcion)s, %(solicitante)s, %(cliente)s, %(tipo)s,
             %(codigo_estatus)s, %(canal)s, %(orden_prioridad)s, %(sr_ebs)s, now(), %(actor)s,
             now(), %(actor)s)
        RETURNING id
        """,
        {
            "nombre": solicitud.titulo,
            "descripcion": solicitud.descripcion,
            "solicitante": solicitante_id,
            "cliente": cliente_id,
            "tipo": tipo_id,
            "codigo_estatus": solicitud.status_cd,
            "canal": canal_id,
            "orden_prioridad": solicitud.orden_prioridad,
            "sr_ebs": solicitud.sr_ebs,
            "actor": actor,
        },
    )
    return cursor.fetchone()[0]


def insert_adjunto(
    cursor,
    id_solicitud: int,
    nombre_archivo: str,
    ruta_almacenamiento: str,
    tipo_mime: str | None,
    tamano_bytes: int,
) -> int:
    cursor.execute(
        """
        INSERT INTO adjuntos (nombre_archivo, ruta_almacenamiento, tipo_mime, tamano_bytes)
        VALUES (%(nombre_archivo)s, %(ruta_almacenamiento)s, %(tipo_mime)s, %(tamano_bytes)s)
        RETURNING id
        """,
        {
            "nombre_archivo": nombre_archivo,
            "ruta_almacenamiento": ruta_almacenamiento,
            "tipo_mime": tipo_mime,
            "tamano_bytes": tamano_bytes,
        },
    )
    id_adjunto = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO solicitudes_adjuntos (solicitud_id, adjunto_id) VALUES (%(id_solicitud)s, %(id_adjunto)s)",
        {"id_solicitud": id_solicitud, "id_adjunto": id_adjunto},
    )
    return id_adjunto


def insert_solicitud_md(cursor, id_solicitud: int, ruta_md: str) -> None:
    cursor.execute(
        "INSERT INTO solicitudes_md (solicitud_id, ruta_md) VALUES (%(id_solicitud)s, %(ruta_md)s)",
        {"id_solicitud": id_solicitud, "ruta_md": ruta_md},
    )


def list_adjuntos_by_solicitud(cursor, solicitud_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT a.id, a.nombre_archivo, a.tipo_mime, a.tamano_bytes, a.fecha_carga
        FROM adjuntos a
        JOIN solicitudes_adjuntos sa ON sa.adjunto_id = a.id
        WHERE sa.solicitud_id = %(solicitud_id)s
        ORDER BY a.fecha_carga
        """,
        {"solicitud_id": solicitud_id},
    )
    columnas = ["id", "nombre_archivo", "tipo_mime", "tamano_bytes", "fecha_carga"]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def get_adjunto_de_solicitud(cursor, solicitud_id: int, adjunto_id: int) -> dict | None:
    """Trae ruta_almacenamiento (no expuesta por list_adjuntos_by_solicitud) para que el
    endpoint de descarga pueda abrir el archivo en disco. El JOIN valida de paso que el
    adjunto realmente pertenezca a esa solicitud, no solo que exista."""
    cursor.execute(
        """
        SELECT a.id, a.nombre_archivo, a.ruta_almacenamiento, a.tipo_mime, a.tamano_bytes
        FROM adjuntos a
        JOIN solicitudes_adjuntos sa ON sa.adjunto_id = a.id
        WHERE sa.solicitud_id = %(solicitud_id)s AND a.id = %(adjunto_id)s
        """,
        {"solicitud_id": solicitud_id, "adjunto_id": adjunto_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = ["id", "nombre_archivo", "ruta_almacenamiento", "tipo_mime", "tamano_bytes"]
    return dict(zip(columnas, row))


def count_adjuntos_by_solicitud(cursor, solicitud_id: int) -> int:
    """Usado para validar el máximo de 5 adjuntos al agregar más a una solicitud ya creada
    (Fase 1.21) — a diferencia de la creación, aquí hay que sumar los que ya existen."""
    cursor.execute(
        "SELECT count(*) FROM solicitudes_adjuntos WHERE solicitud_id = %(solicitud_id)s",
        {"solicitud_id": solicitud_id},
    )
    return cursor.fetchone()[0]


def insert_adjunto_tarea(
    cursor,
    tarea_id: int,
    nombre_archivo: str,
    ruta_almacenamiento: str,
    tipo_mime: str | None,
    tamano_bytes: int,
) -> int:
    """Mismo patrón que insert_adjunto, pero vinculando a tareas_adjuntos (Fase 1.21)."""
    cursor.execute(
        """
        INSERT INTO adjuntos (nombre_archivo, ruta_almacenamiento, tipo_mime, tamano_bytes)
        VALUES (%(nombre_archivo)s, %(ruta_almacenamiento)s, %(tipo_mime)s, %(tamano_bytes)s)
        RETURNING id
        """,
        {
            "nombre_archivo": nombre_archivo,
            "ruta_almacenamiento": ruta_almacenamiento,
            "tipo_mime": tipo_mime,
            "tamano_bytes": tamano_bytes,
        },
    )
    id_adjunto = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO tareas_adjuntos (tarea_id, adjunto_id) VALUES (%(tarea_id)s, %(id_adjunto)s)",
        {"tarea_id": tarea_id, "id_adjunto": id_adjunto},
    )
    return id_adjunto


def list_adjuntos_by_tarea(cursor, tarea_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT a.id, a.nombre_archivo, a.tipo_mime, a.tamano_bytes, a.fecha_carga
        FROM adjuntos a
        JOIN tareas_adjuntos ta ON ta.adjunto_id = a.id
        WHERE ta.tarea_id = %(tarea_id)s
        ORDER BY a.fecha_carga
        """,
        {"tarea_id": tarea_id},
    )
    columnas = ["id", "nombre_archivo", "tipo_mime", "tamano_bytes", "fecha_carga"]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def count_adjuntos_by_tarea(cursor, tarea_id: int) -> int:
    cursor.execute(
        "SELECT count(*) FROM tareas_adjuntos WHERE tarea_id = %(tarea_id)s", {"tarea_id": tarea_id}
    )
    return cursor.fetchone()[0]


def get_adjunto_de_tarea(cursor, tarea_id: int, adjunto_id: int) -> dict | None:
    cursor.execute(
        """
        SELECT a.id, a.nombre_archivo, a.ruta_almacenamiento, a.tipo_mime, a.tamano_bytes
        FROM adjuntos a
        JOIN tareas_adjuntos ta ON ta.adjunto_id = a.id
        WHERE ta.tarea_id = %(tarea_id)s AND a.id = %(adjunto_id)s
        """,
        {"tarea_id": tarea_id, "adjunto_id": adjunto_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = ["id", "nombre_archivo", "ruta_almacenamiento", "tipo_mime", "tamano_bytes"]
    return dict(zip(columnas, row))


def mark_email_processed(cursor, message_id: str, id_solicitud: int | None) -> None:
    cursor.execute(
        "INSERT INTO emails_procesados (email_message_id, solicitud_id) VALUES (%(message_id)s, %(id_solicitud)s)",
        {"message_id": message_id, "id_solicitud": id_solicitud},
    )


def list_miembros(cursor, excluir_externos: bool = False) -> list[dict]:
    condiciones = ["borrado_en IS NULL"]
    if excluir_externos:
        condiciones.append("(codigo_rol_scrum IS NULL OR codigo_rol_scrum != 'EXTERNO')")
    cursor.execute(
        f"SELECT id, usuario, nombre_completo, correo_electronico FROM miembros_equipo "
        f"WHERE {' AND '.join(condiciones)} ORDER BY nombre_completo"
    )
    return [
        {"id": row[0], "usuario": row[1], "nombre_completo": row[2], "correo_electronico": row[3]}
        for row in cursor.fetchall()
    ]


def es_miembro_externo(cursor, miembro_id: int) -> bool:
    """Punto 1 (2026-09-04): un Externo nunca puede ser responsable de tarea, responsable de
    atención de una solicitud, ni responsable de un "por hacer" — solo puede trabajar sus
    propias solicitudes. Devuelve False (no bloquea) si el id ni siquiera existe; el 404 de "no
    encontrado" ya lo maneja cada endpoint por separado al validar el resto del body."""
    cursor.execute("SELECT codigo_rol_scrum FROM miembros_equipo WHERE id = %(id)s", {"id": miembro_id})
    row = cursor.fetchone()
    return row is not None and row[0] == "EXTERNO"


def get_miembro_by_usuario(cursor, usuario: str) -> dict | None:
    """Usado por el login: trae también password_hash/acceso_activo, a diferencia de
    list_miembros (que nunca debe exponer el hash por API)."""
    cursor.execute(
        """
        SELECT id, usuario, nombre_completo, password_hash, codigo_rol_scrum, acceso_activo,
               correo_electronico, debe_cambiar_password
        FROM miembros_equipo
        WHERE usuario ILIKE %(usuario)s
        """,
        {"usuario": usuario},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = [
        "id", "usuario", "nombre_completo", "password_hash", "codigo_rol_scrum", "acceso_activo",
        "correo_electronico", "debe_cambiar_password",
    ]
    return dict(zip(columnas, row))


def get_miembro_by_id(cursor, miembro_id: int) -> dict | None:
    """Usado por get_current_user en cada request, para no confiar solo en el JWT si el
    Scrum Master desactivó el acceso o cambió el rol después de emitido el token."""
    cursor.execute(
        """
        SELECT id, usuario, nombre_completo, password_hash, codigo_rol_scrum, acceso_activo,
               correo_electronico, debe_cambiar_password
        FROM miembros_equipo
        WHERE id = %(id)s
        """,
        {"id": miembro_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = [
        "id", "usuario", "nombre_completo", "password_hash", "codigo_rol_scrum", "acceso_activo",
        "correo_electronico", "debe_cambiar_password",
    ]
    return dict(zip(columnas, row))


def get_miembro_by_email(cursor, correo: str) -> dict | None:
    """Usado por forgot-password. A diferencia de find_miembro_id_by_email (que solo
    resuelve un id para atribuir solicitudes), aquí hace falta el registro completo."""
    cursor.execute(
        """
        SELECT id, usuario, nombre_completo, password_hash, codigo_rol_scrum, acceso_activo,
               correo_electronico, debe_cambiar_password
        FROM miembros_equipo
        WHERE correo_electronico ILIKE %(correo)s
        """,
        {"correo": correo},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = [
        "id", "usuario", "nombre_completo", "password_hash", "codigo_rol_scrum", "acceso_activo",
        "correo_electronico", "debe_cambiar_password",
    ]
    return dict(zip(columnas, row))


def list_miembros_con_acceso(cursor) -> list[dict]:
    cursor.execute(
        """
        SELECT m.id, m.usuario, m.nombre_completo, m.correo_electronico, m.codigo_rol_scrum,
               r.descripcion AS rol_scrum_descripcion, m.acceso_activo
        FROM miembros_equipo m
        LEFT JOIN roles_scrum r ON r.codigo = m.codigo_rol_scrum
        WHERE m.borrado_en IS NULL
        ORDER BY m.nombre_completo
        """
    )
    columnas = [
        "id", "usuario", "nombre_completo", "correo_electronico", "codigo_rol_scrum",
        "rol_scrum_descripcion", "acceso_activo",
    ]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def otorgar_acceso_miembro(cursor, miembro_id: int, password_hash: str, codigo_rol_scrum: str) -> int:
    """La contraseña la elige el Scrum Master, no el propio usuario: se marca
    debe_cambiar_password para forzarlo a fijar la suya en su primer login."""
    cursor.execute(
        """
        UPDATE miembros_equipo
        SET password_hash = %(password_hash)s, codigo_rol_scrum = %(codigo_rol_scrum)s,
            acceso_activo = true, debe_cambiar_password = true,
            actualizado_en = now(), actualizado_por = current_user
        WHERE id = %(id)s
        """,
        {"password_hash": password_hash, "codigo_rol_scrum": codigo_rol_scrum, "id": miembro_id},
    )
    return cursor.rowcount


def crear_miembro(
    cursor, usuario: str, nombre_completo: str, correo_electronico: str | None, actor: str
) -> int:
    """Crea solo la identidad (sin rol/contraseña/acceso) — el miembro nace con
    acceso_activo=false. El segundo paso (otorgar_acceso_miembro, vía POST /{id}/acceso)
    sigue siendo el único que fija password_hash/codigo_rol_scrum. Los índices únicos
    parciales de la migración 009 (sobre borrado_en IS NULL) son los que garantizan
    no-duplicados; el IntegrityError se traduce a 409 en la ruta."""
    cursor.execute(
        """
        INSERT INTO miembros_equipo
            (usuario, nombre_completo, correo_electronico, creado_en, creado_por,
             actualizado_en, actualizado_por)
        VALUES
            (%(usuario)s, %(nombre_completo)s, %(correo_electronico)s, now(), %(actor)s, now(), %(actor)s)
        RETURNING id
        """,
        {
            "usuario": usuario,
            "nombre_completo": nombre_completo,
            "correo_electronico": correo_electronico,
            "actor": actor,
        },
    )
    return cursor.fetchone()[0]


def actualizar_miembro(
    cursor,
    miembro_id: int,
    usuario: str | None,
    nombre_completo: str | None,
    correo_electronico: str | None,
    codigo_rol_scrum: str | None,
    acceso_activo: bool | None,
    password_hash: str | None,
    actor: str,
) -> int:
    """Un único UPDATE con COALESCE por campo (todo opcional): edita identidad
    (usuario/nombre_completo/correo_electronico) y acceso (rol/activo/contraseña) en la
    misma pantalla — formulario unificado de la Fase 1.10. Igual que antes, si viene
    password_hash se fuerza debe_cambiar_password. No permite editar un miembro ya dado de
    baja (borrado_en IS NULL en el WHERE)."""
    cursor.execute(
        """
        UPDATE miembros_equipo
        SET usuario = COALESCE(%(usuario)s, usuario),
            nombre_completo = COALESCE(%(nombre_completo)s, nombre_completo),
            correo_electronico = COALESCE(%(correo_electronico)s, correo_electronico),
            codigo_rol_scrum = COALESCE(%(codigo_rol_scrum)s, codigo_rol_scrum),
            acceso_activo = COALESCE(%(acceso_activo)s, acceso_activo),
            password_hash = COALESCE(%(password_hash)s, password_hash),
            debe_cambiar_password = CASE
                WHEN %(password_hash)s IS NOT NULL THEN true
                ELSE debe_cambiar_password
            END,
            actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s AND borrado_en IS NULL
        """,
        {
            "usuario": usuario,
            "nombre_completo": nombre_completo,
            "correo_electronico": correo_electronico,
            "codigo_rol_scrum": codigo_rol_scrum,
            "acceso_activo": acceso_activo,
            "password_hash": password_hash,
            "id": miembro_id,
            "actor": actor,
        },
    )
    return cursor.rowcount


def dar_de_baja_miembro(cursor, miembro_id: int, actor: str) -> int:
    """Borrado lógico: oculta al miembro de list_miembros/list_miembros_con_acceso y le
    revoca el acceso (get_current_user también exige acceso_activo=true en cada request, así
    que una sesión JWT vigente deja de servir). No toca ningún JOIN de solicitudes/tareas/
    comentarios/hitos hacia miembros_equipo — el histórico sigue mostrando su nombre."""
    cursor.execute(
        """
        UPDATE miembros_equipo
        SET borrado_en = now(), borrado_por = %(actor)s,
            acceso_activo = false,
            actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s AND borrado_en IS NULL
        """,
        {"actor": actor, "id": miembro_id},
    )
    return cursor.rowcount


def set_password_miembro(cursor, miembro_id: int, password_hash: str) -> None:
    """Usado tanto por reset-password (link de correo) como por change-password
    (autoservicio) — en ambos casos el usuario fijó su propia contraseña, así que se limpia
    debe_cambiar_password."""
    cursor.execute(
        """
        UPDATE miembros_equipo
        SET password_hash = %(password_hash)s, debe_cambiar_password = false,
            actualizado_en = now(), actualizado_por = current_user
        WHERE id = %(id)s
        """,
        {"password_hash": password_hash, "id": miembro_id},
    )


def crear_token_reset(cursor, miembro_id: int, token_hash: str, expira_en) -> int:
    cursor.execute(
        """
        INSERT INTO tokens_reset_password (miembro_id, token_hash, expira_en)
        VALUES (%(miembro_id)s, %(token_hash)s, %(expira_en)s)
        RETURNING id
        """,
        {"miembro_id": miembro_id, "token_hash": token_hash, "expira_en": expira_en},
    )
    return cursor.fetchone()[0]


def get_token_reset(cursor, token_hash: str) -> dict | None:
    cursor.execute(
        """
        SELECT id, miembro_id, expira_en, usado_en
        FROM tokens_reset_password
        WHERE token_hash = %(token_hash)s
        """,
        {"token_hash": token_hash},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = ["id", "miembro_id", "expira_en", "usado_en"]
    return dict(zip(columnas, row))


def marcar_token_usado(cursor, token_id: int) -> None:
    cursor.execute(
        "UPDATE tokens_reset_password SET usado_en = now() WHERE id = %(id)s",
        {"id": token_id},
    )


def list_roles_scrum(cursor) -> list[dict]:
    cursor.execute("SELECT codigo, descripcion FROM roles_scrum ORDER BY orden_visualizacion")
    return [{"codigo": row[0], "descripcion": row[1]} for row in cursor.fetchall()]


def list_tipos_solicitud(cursor) -> list[dict]:
    cursor.execute("SELECT id, tipo FROM tipos_solicitud WHERE tipo IS NOT NULL ORDER BY orden")
    return [{"id": row[0], "tipo": row[1]} for row in cursor.fetchall()]


def list_estatus(cursor) -> list[dict]:
    cursor.execute("SELECT codigo, descripcion FROM estatus ORDER BY orden_visualizacion")
    return [{"codigo": row[0], "descripcion": row[1]} for row in cursor.fetchall()]


def get_solicitud_by_id(cursor, solicitud_id: int) -> dict | None:
    """Detalle completo para la vista maestro-detalle: incluye textos legibles de los
    catálogos (para mostrar) y los ids crudos de cliente/tipo (para precargar los <select>
    del formulario de edición)."""
    cursor.execute(
        """
        SELECT s.id, s.nombre, s.descripcion, c.nombre AS cliente, s.cliente AS cliente_id,
               t.tipo AS tipo, s.tipo AS tipo_id, s.codigo_estatus,
               e.descripcion AS estatus_descripcion, m.nombre_completo AS solicitante,
               s.solicitante AS solicitante_id,
               s.orden_prioridad, cs.canal AS canal, s.canal AS canal_id,
               s.fecha_completado, s.fecha_entrega, s.responsable_atencion_id,
               ra.nombre_completo AS responsable_atencion,
               coalesce(ra.perfil, 'Sin área') AS responsable_atencion_area,
               s.sr_ebs,
               s.creado_en, s.actualizado_en, s.actualizado_por
        FROM solicitudes s
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN tipos_solicitud t ON t.id = s.tipo
        LEFT JOIN estatus e ON e.codigo = s.codigo_estatus
        LEFT JOIN miembros_equipo m ON m.id = s.solicitante
        LEFT JOIN canales_solicitud cs ON cs.id = s.canal
        LEFT JOIN miembros_equipo ra ON ra.id = s.responsable_atencion_id
        WHERE s.id = %(id)s AND s.borrado_en IS NULL
        """,
        {"id": solicitud_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = [
        "id", "nombre", "descripcion", "cliente", "cliente_id", "tipo", "tipo_id",
        "codigo_estatus", "estatus_descripcion", "solicitante", "solicitante_id", "orden_prioridad",
        "canal", "canal_id", "fecha_completado", "fecha_entrega", "responsable_atencion_id",
        "responsable_atencion", "responsable_atencion_area", "sr_ebs",
        "creado_en", "actualizado_en", "actualizado_por",
    ]
    return dict(zip(columnas, row))


def update_solicitud(
    cursor,
    solicitud_id: int,
    nombre: str,
    descripcion: str,
    cliente_id: int | None,
    tipo_id: int | None,
    canal_id: int | None,
    codigo_estatus: str,
    orden_prioridad: int,
    fecha_completado,
    fecha_entrega,
    responsable_atencion_id: int | None,
    actor: str,
    sr_ebs: str | None = None,
) -> int:
    # fecha_completado solo tiene sentido si el estatus es Completado: si se cambia a
    # cualquier otro estatus, se limpia sin importar qué haya llegado en el body.
    fecha_completado_final = fecha_completado if codigo_estatus == "COMPLETADO" else None
    cursor.execute(
        """
        UPDATE solicitudes
        SET nombre = %(nombre)s, descripcion = %(descripcion)s, cliente = %(cliente)s,
            tipo = %(tipo)s, canal = %(canal)s, codigo_estatus = %(codigo_estatus)s,
            orden_prioridad = %(orden_prioridad)s, fecha_completado = %(fecha_completado)s,
            fecha_entrega = %(fecha_entrega)s, responsable_atencion_id = %(responsable_atencion_id)s,
            sr_ebs = %(sr_ebs)s, actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s AND borrado_en IS NULL
        """,
        {
            "nombre": nombre,
            "descripcion": descripcion,
            "cliente": cliente_id,
            "tipo": tipo_id,
            "canal": canal_id,
            "codigo_estatus": codigo_estatus,
            "orden_prioridad": orden_prioridad,
            "fecha_completado": fecha_completado_final,
            "fecha_entrega": fecha_entrega,
            "responsable_atencion_id": responsable_atencion_id,
            "sr_ebs": sr_ebs,
            "id": solicitud_id,
            "actor": actor,
        },
    )
    return cursor.rowcount


def update_solicitud_externo(
    cursor,
    solicitud_id: int,
    *,
    nombre: str,
    descripcion: str,
    cliente_id: int | None,
    tipo_id: int | None,
    actor: str,
) -> int:
    """Edición restringida para el rol EXTERNO (Fase de rol Externo): solo los mismos 4 campos
    que ya puede llenar al crear la solicitud — nunca estatus/prioridad/fechas/responsable de
    atención, esos los controla el equipo interno. El endpoint que llama a esto ya verificó
    dueño y que la solicitud sigue en "EN ESPERA" antes de llegar aquí."""
    cursor.execute(
        """
        UPDATE solicitudes
        SET nombre = %(nombre)s, descripcion = %(descripcion)s, cliente = %(cliente)s,
            tipo = %(tipo)s, actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s AND borrado_en IS NULL
        """,
        {
            "nombre": nombre,
            "descripcion": descripcion,
            "cliente": cliente_id,
            "tipo": tipo_id,
            "id": solicitud_id,
            "actor": actor,
        },
    )
    return cursor.rowcount


def marcar_solicitud_en_progreso(cursor, solicitud_id: int, actor: str) -> int:
    """Punto 4 (2026-09-04): al inicializarse una tarea (pasar a "En progreso"), la solicitud
    pasa sola a "En progreso" — pero solo si seguía en "Planeado". La condición va en el WHERE
    (no antes, en un SELECT aparte) para que sea atómica y para que el caller pueda llamarla sin
    condicional propio: si la solicitud ya no está en Planeado, simplemente no afecta filas."""
    cursor.execute(
        """
        UPDATE solicitudes
        SET codigo_estatus = 'EN PROGRESO', actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s AND codigo_estatus = 'PLANEADO' AND borrado_en IS NULL
        """,
        {"id": solicitud_id, "actor": actor},
    )
    return cursor.rowcount


def delete_solicitud(cursor, solicitud_id: int, actor: str) -> int:
    """Borrado lógico: la solicitud y su información dependiente (tareas, comentarios,
    hitos) quedan marcadas con borrado_en/borrado_por en vez de desaparecer — así se puede
    saber quién borró qué y cuándo. Ya no hace falta tocar solicitudes_adjuntos/adjuntos/
    solicitudes_md/emails_procesados: como la solicitud sigue existiendo (solo marcada como
    borrada), esas filas siguen siendo válidas apuntando a ella."""
    cursor.execute(
        "UPDATE tareas SET borrado_en = now(), borrado_por = %(actor)s WHERE solicitud_id = %(id)s AND borrado_en IS NULL",
        {"actor": actor, "id": solicitud_id},
    )
    cursor.execute(
        "UPDATE comentarios SET borrado_en = now(), borrado_por = %(actor)s WHERE solicitud_id = %(id)s AND borrado_en IS NULL",
        {"actor": actor, "id": solicitud_id},
    )
    cursor.execute(
        "UPDATE hitos SET borrado_en = now(), borrado_por = %(actor)s WHERE solicitud_id = %(id)s AND borrado_en IS NULL",
        {"actor": actor, "id": solicitud_id},
    )
    cursor.execute(
        "UPDATE solicitudes SET borrado_en = now(), borrado_por = %(actor)s WHERE id = %(id)s AND borrado_en IS NULL",
        {"actor": actor, "id": solicitud_id},
    )
    return cursor.rowcount


def list_estatus_tarea(cursor) -> list[dict]:
    cursor.execute("SELECT codigo, descripcion FROM estatus_tarea ORDER BY orden_visualizacion")
    return [{"codigo": row[0], "descripcion": row[1]} for row in cursor.fetchall()]


def list_tareas(
    cursor,
    cliente: str | None = None,
    responsable_id: int | None = None,
    limit: int = 200,
) -> list[dict]:
    """Listado global para el Tablero Scrum: todas las tareas de todas las solicitudes,
    con el mismo shape que get_tarea_by_id (necesario para que el PUT de drag-and-drop no
    borre campos que no vienen en la tarjeta) más solicitud_nombre/cliente de referencia."""
    condiciones = ["t.borrado_en IS NULL"]
    parametros: dict = {"max_rows": limit}
    if cliente:
        condiciones.append("c.nombre ILIKE %(cliente)s")
        parametros["cliente"] = f"%{cliente}%"
    if responsable_id:
        condiciones.append("t.responsable_id = %(responsable_id)s")
        parametros["responsable_id"] = responsable_id

    where = f"WHERE {' AND '.join(condiciones)}"
    cursor.execute(
        f"""
        SELECT t.id, t.solicitud_id, s.nombre AS solicitud_nombre, c.nombre AS cliente,
               t.nombre, t.descripcion, t.responsable_id, m.nombre_completo AS responsable,
               s.orden_prioridad AS solicitud_prioridad, s.fecha_entrega AS solicitud_fecha_entrega,
               s.codigo_estatus AS solicitud_codigo_estatus,
               t.codigo_estatus_tarea, et.descripcion AS estatus_tarea_descripcion,
               t.fecha_inicio, t.fecha_fin, t.fecha_inicio_real, t.fecha_fin_real,
               t.horas_estimadas, t.horas_reales, t.creado_en, t.actualizado_en
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN miembros_equipo m ON m.id = t.responsable_id
        LEFT JOIN estatus_tarea et ON et.codigo = t.codigo_estatus_tarea
        {where}
        ORDER BY t.creado_en
        LIMIT %(max_rows)s
        """,
        parametros,
    )
    columnas = [
        "id", "solicitud_id", "solicitud_nombre", "cliente", "nombre", "descripcion",
        "responsable_id", "responsable", "solicitud_prioridad", "solicitud_fecha_entrega",
        "solicitud_codigo_estatus",
        "codigo_estatus_tarea", "estatus_tarea_descripcion", "fecha_inicio", "fecha_fin",
        "fecha_inicio_real", "fecha_fin_real", "horas_estimadas", "horas_reales",
        "creado_en", "actualizado_en",
    ]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


_COLUMNAS_TAREA_MONITOR = [
    "id", "solicitud_id", "solicitud_nombre", "cliente", "nombre", "responsable_id",
    "responsable", "codigo_estatus_tarea", "estatus_tarea_descripcion", "fecha_fin", "dias",
]


def list_tareas_vencidas(cursor, hoy: date) -> list[dict]:
    """Tareas activas, no completadas, cuya fecha_fin planeada ya pasó. `dias` = días de
    atraso (positivo)."""
    cursor.execute(
        """
        SELECT t.id, t.solicitud_id, s.nombre AS solicitud_nombre, c.nombre AS cliente,
               t.nombre, t.responsable_id, m.nombre_completo AS responsable,
               t.codigo_estatus_tarea, et.descripcion AS estatus_tarea_descripcion,
               t.fecha_fin, (%(hoy)s - t.fecha_fin) AS dias
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN miembros_equipo m ON m.id = t.responsable_id
        LEFT JOIN estatus_tarea et ON et.codigo = t.codigo_estatus_tarea
        WHERE t.borrado_en IS NULL AND t.codigo_estatus_tarea NOT IN ('COMPLETADO', 'CANCELADO')
          AND t.fecha_fin < %(hoy)s
        ORDER BY t.fecha_fin
        """,
        {"hoy": hoy},
    )
    return [dict(zip(_COLUMNAS_TAREA_MONITOR, row)) for row in cursor.fetchall()]


def list_tareas_por_vencer(cursor, hoy: date, dias_ventana: int = 7) -> list[dict]:
    """Tareas activas, no completadas, cuya fecha_fin planeada cae dentro de los próximos
    `dias_ventana` días. `dias` = días restantes (positivo, 0 = vence hoy)."""
    cursor.execute(
        """
        SELECT t.id, t.solicitud_id, s.nombre AS solicitud_nombre, c.nombre AS cliente,
               t.nombre, t.responsable_id, m.nombre_completo AS responsable,
               t.codigo_estatus_tarea, et.descripcion AS estatus_tarea_descripcion,
               t.fecha_fin, (t.fecha_fin - %(hoy)s) AS dias
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN miembros_equipo m ON m.id = t.responsable_id
        LEFT JOIN estatus_tarea et ON et.codigo = t.codigo_estatus_tarea
        WHERE t.borrado_en IS NULL AND t.codigo_estatus_tarea NOT IN ('COMPLETADO', 'CANCELADO')
          AND t.fecha_fin >= %(hoy)s AND t.fecha_fin <= %(limite)s
        ORDER BY t.fecha_fin
        """,
        {"hoy": hoy, "limite": hoy + timedelta(days=dias_ventana)},
    )
    return [dict(zip(_COLUMNAS_TAREA_MONITOR, row)) for row in cursor.fetchall()]


def list_carga_por_responsable(cursor) -> list[dict]:
    """Tareas activas no completadas por responsable, incluye un bucket responsable_id=NULL
    ('Sin asignar')."""
    cursor.execute(
        """
        SELECT t.responsable_id, m.nombre_completo AS responsable, count(*) AS tareas_abiertas
        FROM tareas t
        LEFT JOIN miembros_equipo m ON m.id = t.responsable_id
        WHERE t.borrado_en IS NULL AND t.codigo_estatus_tarea NOT IN ('COMPLETADO', 'CANCELADO')
        GROUP BY t.responsable_id, m.nombre_completo
        ORDER BY tareas_abiertas DESC, responsable NULLS LAST
        """
    )
    columnas = ["responsable_id", "responsable", "tareas_abiertas"]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def list_distribucion_estatus(cursor) -> list[dict]:
    """Cuántas tareas activas hay en cada estatus del catálogo (incluye estatus en 0)."""
    cursor.execute(
        """
        SELECT et.codigo, et.descripcion, count(t.id) AS total
        FROM estatus_tarea et
        LEFT JOIN tareas t ON t.codigo_estatus_tarea = et.codigo AND t.borrado_en IS NULL
        GROUP BY et.codigo, et.descripcion, et.orden_visualizacion
        ORDER BY et.orden_visualizacion
        """
    )
    columnas = ["codigo_estatus_tarea", "descripcion", "total"]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def get_cumplimiento_planeado_real(cursor) -> dict:
    """Entre las tareas con fecha_fin_real registrada, cuántas cumplieron fecha_fin
    planeada vs. cuántas se atrasaron, y el atraso promedio (en días) de las atrasadas."""
    cursor.execute(
        """
        SELECT
            count(*) AS total_con_fecha_real,
            count(*) FILTER (WHERE fecha_fin_real <= fecha_fin) AS cumplidas,
            count(*) FILTER (WHERE fecha_fin_real > fecha_fin) AS atrasadas,
            avg(fecha_fin_real - fecha_fin) FILTER (WHERE fecha_fin_real > fecha_fin) AS promedio_atraso
        FROM tareas
        WHERE borrado_en IS NULL AND fecha_fin_real IS NOT NULL
        """
    )
    total, cumplidas, atrasadas, promedio = cursor.fetchone()
    return {
        "total_con_fecha_real": total,
        "cumplidas": cumplidas,
        "atrasadas": atrasadas,
        "porcentaje_cumplimiento": round(cumplidas / total * 100, 1) if total else None,
        "promedio_dias_atraso": round(float(promedio), 1) if promedio is not None else None,
    }


def get_direccion_general_totales(cursor, desde: date, hasta: date) -> dict:
    """KPIs agregados de toda la organización para el tablero de Dirección General
    (Fase 1.15): 'en proceso' es un snapshot (no depende del rango); el resto se filtra por
    [desde, hasta]. Horas estimadas = de tareas cuya solicitud padre fue creada en el rango."""
    cursor.execute(
        """
        SELECT
            count(*) FILTER (WHERE codigo_estatus NOT IN ('COMPLETADO', 'CANCELADO')),
            count(*) FILTER (
                WHERE codigo_estatus = 'COMPLETADO'
                AND fecha_completado::date BETWEEN %(desde)s AND %(hasta)s
            ),
            count(*) FILTER (WHERE creado_en::date BETWEEN %(desde)s AND %(hasta)s)
        FROM solicitudes
        WHERE borrado_en IS NULL
        """,
        {"desde": desde, "hasta": hasta},
    )
    sol_en_proceso, sol_concluidas, sol_nuevas = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            count(*) FILTER (WHERE t.codigo_estatus_tarea NOT IN ('COMPLETADO', 'CANCELADO')),
            count(*) FILTER (
                WHERE t.codigo_estatus_tarea = 'COMPLETADO'
                AND t.fecha_fin_real BETWEEN %(desde)s AND %(hasta)s
            ),
            count(*) FILTER (WHERE t.creado_en::date BETWEEN %(desde)s AND %(hasta)s),
            coalesce(sum(t.horas_estimadas) FILTER (
                WHERE s.creado_en::date BETWEEN %(desde)s AND %(hasta)s
            ), 0)
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id AND s.borrado_en IS NULL
        WHERE t.borrado_en IS NULL
        """,
        {"desde": desde, "hasta": hasta},
    )
    tarea_en_proceso, tarea_concluidas, tarea_nuevas, horas_periodo = cursor.fetchone()

    return {
        "solicitudes_en_proceso": sol_en_proceso,
        "tareas_en_proceso": tarea_en_proceso,
        "solicitudes_concluidas_periodo": sol_concluidas,
        "tareas_concluidas_periodo": tarea_concluidas,
        "solicitudes_nuevas_periodo": sol_nuevas,
        "tareas_nuevas_periodo": tarea_nuevas,
        "horas_estimadas_periodo": int(horas_periodo),
    }


def _combinar_por_grupo(filas_solicitudes: list[dict], filas_tareas: list[dict]) -> list[dict]:
    """Combina el lado 'solicitudes' y el lado 'tareas' de un desglose por dimensión
    (cliente/tipo/área) del tablero de Dirección General. Cada lado ya viene agregado por
    separado (evita el fan-out de un JOIN solicitudes+tareas agrupado, que multiplicaría los
    conteos); acá solo se combinan por `grupo_id`, rellenando con 0 el lado sin filas."""
    combinado: dict[object, dict] = {}
    for fila in filas_solicitudes:
        combinado[fila["grupo_id"]] = {
            "grupo_id": fila["grupo_id"],
            "grupo": fila["grupo"],
            "solicitudes_en_proceso": fila["en_proceso"],
            "solicitudes_concluidas_periodo": fila["concluidas_periodo"],
            "solicitudes_nuevas_periodo": fila["nuevas_periodo"],
            "tareas_en_proceso": 0,
            "tareas_concluidas_periodo": 0,
            "tareas_nuevas_periodo": 0,
            "horas_estimadas_periodo": 0,
        }
    for fila in filas_tareas:
        grupo = combinado.setdefault(
            fila["grupo_id"],
            {
                "grupo_id": fila["grupo_id"],
                "grupo": fila["grupo"],
                "solicitudes_en_proceso": 0,
                "solicitudes_concluidas_periodo": 0,
                "solicitudes_nuevas_periodo": 0,
                "tareas_en_proceso": 0,
                "tareas_concluidas_periodo": 0,
                "tareas_nuevas_periodo": 0,
                "horas_estimadas_periodo": 0,
            },
        )
        grupo["tareas_en_proceso"] = fila["en_proceso"]
        grupo["tareas_concluidas_periodo"] = fila["concluidas_periodo"]
        grupo["tareas_nuevas_periodo"] = fila["nuevas_periodo"]
        grupo["horas_estimadas_periodo"] = fila["horas_estimadas_periodo"]
    return sorted(combinado.values(), key=lambda f: str(f["grupo"]))


def list_direccion_general_por_cliente(cursor, desde: date, hasta: date) -> list[dict]:
    """Desglose por cliente para el tablero de Dirección General (Fase 1.15)."""
    cursor.execute(
        """
        SELECT
            c.id, c.nombre,
            count(*) FILTER (WHERE s.codigo_estatus NOT IN ('COMPLETADO', 'CANCELADO')),
            count(*) FILTER (
                WHERE s.codigo_estatus = 'COMPLETADO'
                AND s.fecha_completado::date BETWEEN %(desde)s AND %(hasta)s
            ),
            count(*) FILTER (WHERE s.creado_en::date BETWEEN %(desde)s AND %(hasta)s)
        FROM solicitudes s
        JOIN clientes c ON c.id = s.cliente
        WHERE s.borrado_en IS NULL
        GROUP BY c.id, c.nombre
        """,
        {"desde": desde, "hasta": hasta},
    )
    columnas = ["grupo_id", "grupo", "en_proceso", "concluidas_periodo", "nuevas_periodo"]
    filas_solicitudes = [dict(zip(columnas, row)) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT
            c.id, c.nombre,
            count(*) FILTER (WHERE t.codigo_estatus_tarea NOT IN ('COMPLETADO', 'CANCELADO')),
            count(*) FILTER (
                WHERE t.codigo_estatus_tarea = 'COMPLETADO'
                AND t.fecha_fin_real BETWEEN %(desde)s AND %(hasta)s
            ),
            count(*) FILTER (WHERE t.creado_en::date BETWEEN %(desde)s AND %(hasta)s),
            coalesce(sum(t.horas_estimadas) FILTER (
                WHERE s.creado_en::date BETWEEN %(desde)s AND %(hasta)s
            ), 0)
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id AND s.borrado_en IS NULL
        JOIN clientes c ON c.id = s.cliente
        WHERE t.borrado_en IS NULL
        GROUP BY c.id, c.nombre
        """,
        {"desde": desde, "hasta": hasta},
    )
    columnas_tareas = [
        "grupo_id", "grupo", "en_proceso", "concluidas_periodo", "nuevas_periodo",
        "horas_estimadas_periodo",
    ]
    filas_tareas = [dict(zip(columnas_tareas, row)) for row in cursor.fetchall()]

    return _combinar_por_grupo(filas_solicitudes, filas_tareas)


def list_direccion_general_por_tipo(cursor, desde: date, hasta: date) -> list[dict]:
    """Desglose por tipo de solicitud para el tablero de Dirección General (Fase 1.15)."""
    cursor.execute(
        """
        SELECT
            tp.id, tp.tipo,
            count(*) FILTER (WHERE s.codigo_estatus NOT IN ('COMPLETADO', 'CANCELADO')),
            count(*) FILTER (
                WHERE s.codigo_estatus = 'COMPLETADO'
                AND s.fecha_completado::date BETWEEN %(desde)s AND %(hasta)s
            ),
            count(*) FILTER (WHERE s.creado_en::date BETWEEN %(desde)s AND %(hasta)s)
        FROM solicitudes s
        JOIN tipos_solicitud tp ON tp.id = s.tipo
        WHERE s.borrado_en IS NULL
        GROUP BY tp.id, tp.tipo
        """,
        {"desde": desde, "hasta": hasta},
    )
    columnas = ["grupo_id", "grupo", "en_proceso", "concluidas_periodo", "nuevas_periodo"]
    filas_solicitudes = [dict(zip(columnas, row)) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT
            tp.id, tp.tipo,
            count(*) FILTER (WHERE t.codigo_estatus_tarea NOT IN ('COMPLETADO', 'CANCELADO')),
            count(*) FILTER (
                WHERE t.codigo_estatus_tarea = 'COMPLETADO'
                AND t.fecha_fin_real BETWEEN %(desde)s AND %(hasta)s
            ),
            count(*) FILTER (WHERE t.creado_en::date BETWEEN %(desde)s AND %(hasta)s),
            coalesce(sum(t.horas_estimadas) FILTER (
                WHERE s.creado_en::date BETWEEN %(desde)s AND %(hasta)s
            ), 0)
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id AND s.borrado_en IS NULL
        JOIN tipos_solicitud tp ON tp.id = s.tipo
        WHERE t.borrado_en IS NULL
        GROUP BY tp.id, tp.tipo
        """,
        {"desde": desde, "hasta": hasta},
    )
    columnas_tareas = [
        "grupo_id", "grupo", "en_proceso", "concluidas_periodo", "nuevas_periodo",
        "horas_estimadas_periodo",
    ]
    filas_tareas = [dict(zip(columnas_tareas, row)) for row in cursor.fetchall()]

    return _combinar_por_grupo(filas_solicitudes, filas_tareas)


def list_direccion_general_por_area(cursor, desde: date, hasta: date) -> list[dict]:
    """Desglose por área (perfil del miembro) para el tablero de Dirección General (Fase
    1.15). El lado solicitudes usa el perfil del *solicitante*; el lado tareas usa el perfil
    del *responsable* — son roles distintos (quién pidió vs. quién ejecuta) unidos por la
    misma etiqueta de área a propósito, para leer demanda vs. capacidad por área."""
    cursor.execute(
        """
        SELECT
            coalesce(m.perfil, 'Sin área'),
            count(*) FILTER (WHERE s.codigo_estatus NOT IN ('COMPLETADO', 'CANCELADO')),
            count(*) FILTER (
                WHERE s.codigo_estatus = 'COMPLETADO'
                AND s.fecha_completado::date BETWEEN %(desde)s AND %(hasta)s
            ),
            count(*) FILTER (WHERE s.creado_en::date BETWEEN %(desde)s AND %(hasta)s)
        FROM solicitudes s
        LEFT JOIN miembros_equipo m ON m.id = s.solicitante
        WHERE s.borrado_en IS NULL
        GROUP BY coalesce(m.perfil, 'Sin área')
        """,
        {"desde": desde, "hasta": hasta},
    )
    filas_solicitudes = [
        {
            "grupo_id": grupo,
            "grupo": grupo,
            "en_proceso": en_proceso,
            "concluidas_periodo": concluidas,
            "nuevas_periodo": nuevas,
        }
        for grupo, en_proceso, concluidas, nuevas in cursor.fetchall()
    ]

    cursor.execute(
        """
        SELECT
            coalesce(m.perfil, 'Sin área'),
            count(*) FILTER (WHERE t.codigo_estatus_tarea NOT IN ('COMPLETADO', 'CANCELADO')),
            count(*) FILTER (
                WHERE t.codigo_estatus_tarea = 'COMPLETADO'
                AND t.fecha_fin_real BETWEEN %(desde)s AND %(hasta)s
            ),
            count(*) FILTER (WHERE t.creado_en::date BETWEEN %(desde)s AND %(hasta)s),
            coalesce(sum(t.horas_estimadas) FILTER (
                WHERE s.creado_en::date BETWEEN %(desde)s AND %(hasta)s
            ), 0)
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id AND s.borrado_en IS NULL
        LEFT JOIN miembros_equipo m ON m.id = t.responsable_id
        WHERE t.borrado_en IS NULL
        GROUP BY coalesce(m.perfil, 'Sin área')
        """,
        {"desde": desde, "hasta": hasta},
    )
    filas_tareas = [
        {
            "grupo_id": grupo,
            "grupo": grupo,
            "en_proceso": en_proceso,
            "concluidas_periodo": concluidas,
            "nuevas_periodo": nuevas,
            "horas_estimadas_periodo": int(horas),
        }
        for grupo, en_proceso, concluidas, nuevas, horas in cursor.fetchall()
    ]

    return _combinar_por_grupo(filas_solicitudes, filas_tareas)


_FILTRO_DETALLE_POR_METRICA = {
    "en_proceso": "s.codigo_estatus NOT IN ('COMPLETADO', 'CANCELADO')",
    "concluidas": (
        "s.codigo_estatus = 'COMPLETADO' AND s.fecha_completado::date BETWEEN %(desde)s AND %(hasta)s"
    ),
    "nuevas": "s.creado_en::date BETWEEN %(desde)s AND %(hasta)s",
}


def list_direccion_general_detalle_solicitudes(
    cursor, metrica: str, desde: date, hasta: date
) -> list[dict]:
    """Solicitudes individuales detrás de una de las 3 métricas de conteo de solicitudes del
    tablero de Dirección General (Fase 1.15+, subvista por métrica). Mismo criterio de filtro
    que `get_direccion_general_totales` para cada métrica — 'en_proceso' es un snapshot, ignora
    desde/hasta, igual que el tile."""
    filtro = _FILTRO_DETALLE_POR_METRICA[metrica]
    cursor.execute(
        f"""
        SELECT s.id, s.nombre, c.nombre AS cliente, coalesce(m.perfil, 'Sin área') AS area,
               m.nombre_completo AS solicitante, s.creado_en
        FROM solicitudes s
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN miembros_equipo m ON m.id = s.solicitante
        WHERE s.borrado_en IS NULL AND {filtro}
        ORDER BY s.creado_en DESC
        """,
        {"desde": desde, "hasta": hasta},
    )
    columnas = ["id", "nombre", "cliente", "area", "solicitante", "creado_en"]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def list_distribucion_estatus_solicitud(cursor) -> list[dict]:
    """Cuántas solicitudes activas hay en cada estatus del catálogo (incluye estatus en 0).
    Equivalente a `list_distribucion_estatus` pero del lado de solicitudes — son catálogos
    distintos (`estatus` vs. `estatus_tarea`), no se combinan en una sola tabla."""
    cursor.execute(
        """
        SELECT e.codigo, e.descripcion, count(s.id) AS total
        FROM estatus e
        LEFT JOIN solicitudes s ON s.codigo_estatus = e.codigo AND s.borrado_en IS NULL
        GROUP BY e.codigo, e.descripcion, e.orden_visualizacion
        ORDER BY e.orden_visualizacion
        """
    )
    columnas = ["codigo_estatus", "descripcion", "total"]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def list_tareas_by_solicitud(cursor, solicitud_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT t.id, t.solicitud_id, t.nombre, t.descripcion, t.responsable_id,
               m.nombre_completo AS responsable, s.orden_prioridad AS solicitud_prioridad,
               s.fecha_entrega AS solicitud_fecha_entrega,
               s.codigo_estatus AS solicitud_codigo_estatus,
               t.codigo_estatus_tarea,
               et.descripcion AS estatus_tarea_descripcion, t.fecha_inicio, t.fecha_fin,
               t.fecha_inicio_real, t.fecha_fin_real, t.horas_estimadas, t.horas_reales,
               t.creado_en, t.actualizado_en
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id
        LEFT JOIN miembros_equipo m ON m.id = t.responsable_id
        LEFT JOIN estatus_tarea et ON et.codigo = t.codigo_estatus_tarea
        WHERE t.solicitud_id = %(id)s AND t.borrado_en IS NULL
        ORDER BY t.creado_en
        """,
        {"id": solicitud_id},
    )
    columnas = [
        "id", "solicitud_id", "nombre", "descripcion", "responsable_id", "responsable",
        "solicitud_prioridad", "solicitud_fecha_entrega", "solicitud_codigo_estatus",
        "codigo_estatus_tarea",
        "estatus_tarea_descripcion", "fecha_inicio", "fecha_fin", "fecha_inicio_real",
        "fecha_fin_real", "horas_estimadas", "horas_reales", "creado_en", "actualizado_en",
    ]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def insert_tarea(
    cursor,
    solicitud_id: int,
    nombre: str,
    descripcion: str | None,
    responsable_id: int | None,
    codigo_estatus_tarea: str,
    actor: str,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    fecha_inicio_real: date | None = None,
    fecha_fin_real: date | None = None,
    horas_estimadas: int | None = None,
    horas_reales: int | None = None,
) -> int:
    """fecha_inicio/fecha_fin (planeadas) son NOT NULL: si el formulario no las captura, se
    inicializan en el backend (hoy / hoy + 7 días). fecha_inicio_real/fecha_fin_real son
    nullable: quedan en NULL hasta que se sepa cuándo arrancó/terminó de verdad la tarea."""
    cursor.execute(
        """
        INSERT INTO tareas
            (solicitud_id, nombre, descripcion, responsable_id, codigo_estatus_tarea,
             fecha_inicio, fecha_fin, fecha_inicio_real, fecha_fin_real,
             horas_estimadas, horas_reales,
             creado_en, creado_por, actualizado_en, actualizado_por)
        VALUES
            (%(solicitud_id)s, %(nombre)s, %(descripcion)s, %(responsable_id)s, %(codigo_estatus_tarea)s,
             COALESCE(%(fecha_inicio)s, now()::date),
             COALESCE(%(fecha_fin)s, (now() + interval '7 days')::date),
             %(fecha_inicio_real)s, %(fecha_fin_real)s,
             %(horas_estimadas)s, %(horas_reales)s, now(), %(actor)s, now(), %(actor)s)
        RETURNING id
        """,
        {
            "solicitud_id": solicitud_id,
            "nombre": nombre,
            "descripcion": descripcion,
            "responsable_id": responsable_id,
            "codigo_estatus_tarea": codigo_estatus_tarea,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "fecha_inicio_real": fecha_inicio_real,
            "fecha_fin_real": fecha_fin_real,
            "horas_estimadas": horas_estimadas,
            "horas_reales": horas_reales,
            "actor": actor,
        },
    )
    return cursor.fetchone()[0]


def update_tarea(
    cursor,
    tarea_id: int,
    nombre: str,
    descripcion: str | None,
    responsable_id: int | None,
    codigo_estatus_tarea: str,
    actor: str,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    fecha_inicio_real: date | None = None,
    fecha_fin_real: date | None = None,
    horas_estimadas: int | None = None,
    horas_reales: int | None = None,
) -> int:
    """fecha_inicio/fecha_fin (planeadas) son NOT NULL: si no se envían, se conserva el
    valor actual (COALESCE) en vez de fallar. fecha_inicio_real/fecha_fin_real, igual que
    horas_estimadas/horas_reales, sí son nullable: se sobrescriben tal cual, incluyendo a
    NULL si el formulario las deja vacías (permite corregir una fecha real capturada de más)."""
    cursor.execute(
        """
        UPDATE tareas
        SET nombre = %(nombre)s, descripcion = %(descripcion)s,
            responsable_id = %(responsable_id)s, codigo_estatus_tarea = %(codigo_estatus_tarea)s,
            fecha_inicio = COALESCE(%(fecha_inicio)s, fecha_inicio),
            fecha_fin = COALESCE(%(fecha_fin)s, fecha_fin),
            fecha_inicio_real = %(fecha_inicio_real)s, fecha_fin_real = %(fecha_fin_real)s,
            horas_estimadas = %(horas_estimadas)s, horas_reales = %(horas_reales)s,
            actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s AND borrado_en IS NULL
        """,
        {
            "nombre": nombre,
            "descripcion": descripcion,
            "responsable_id": responsable_id,
            "codigo_estatus_tarea": codigo_estatus_tarea,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "fecha_inicio_real": fecha_inicio_real,
            "fecha_fin_real": fecha_fin_real,
            "horas_estimadas": horas_estimadas,
            "horas_reales": horas_reales,
            "id": tarea_id,
            "actor": actor,
        },
    )
    return cursor.rowcount


def get_tarea_by_id(cursor, tarea_id: int) -> dict | None:
    cursor.execute(
        """
        SELECT t.id, t.solicitud_id, s.nombre AS solicitud_nombre, c.nombre AS cliente,
               t.nombre, t.descripcion, t.responsable_id,
               m.nombre_completo AS responsable, s.orden_prioridad AS solicitud_prioridad,
               s.fecha_entrega AS solicitud_fecha_entrega,
               s.codigo_estatus AS solicitud_codigo_estatus,
               t.codigo_estatus_tarea,
               et.descripcion AS estatus_tarea_descripcion, t.fecha_inicio, t.fecha_fin,
               t.fecha_inicio_real, t.fecha_fin_real, t.horas_estimadas, t.horas_reales,
               t.creado_en, t.actualizado_en
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN miembros_equipo m ON m.id = t.responsable_id
        LEFT JOIN estatus_tarea et ON et.codigo = t.codigo_estatus_tarea
        WHERE t.id = %(id)s AND t.borrado_en IS NULL
        """,
        {"id": tarea_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = [
        "id", "solicitud_id", "solicitud_nombre", "cliente", "nombre", "descripcion",
        "responsable_id", "responsable", "solicitud_prioridad", "solicitud_fecha_entrega",
        "solicitud_codigo_estatus", "codigo_estatus_tarea",
        "estatus_tarea_descripcion", "fecha_inicio", "fecha_fin", "fecha_inicio_real",
        "fecha_fin_real", "horas_estimadas", "horas_reales", "creado_en", "actualizado_en",
    ]
    return dict(zip(columnas, row))


def delete_tarea(cursor, tarea_id: int, actor: str) -> int:
    """Borrado lógico. enlaces_tarea y tarea_por_hacer se borran físicos solos vía
    ON DELETE CASCADE (son detalle interno, no una de las 4 entidades con auditoría
    pedida); el hito propio de la tarea y sus comentarios se marcan borrados también
    (cascada manual, igual que en delete_solicitud)."""
    cursor.execute(
        "SELECT hito_id FROM tareas WHERE id = %(id)s AND borrado_en IS NULL", {"id": tarea_id}
    )
    row = cursor.fetchone()
    if row is None:
        return 0
    hito_id = row[0]

    cursor.execute(
        "UPDATE comentarios SET borrado_en = now(), borrado_por = %(actor)s WHERE tarea_id = %(id)s AND borrado_en IS NULL",
        {"actor": actor, "id": tarea_id},
    )
    if hito_id:
        cursor.execute(
            "UPDATE hitos SET borrado_en = now(), borrado_por = %(actor)s WHERE id = %(hito_id)s AND borrado_en IS NULL",
            {"actor": actor, "hito_id": hito_id},
        )
    cursor.execute(
        "UPDATE tareas SET borrado_en = now(), borrado_por = %(actor)s WHERE id = %(id)s AND borrado_en IS NULL",
        {"actor": actor, "id": tarea_id},
    )
    return cursor.rowcount


_COLUMNAS_HITO = [
    "id", "solicitud_id", "tarea_id", "tarea_nombre", "nombre", "descripcion",
    "fecha_vencimiento", "creado_en", "creado_por", "creado_por_nombre", "actualizado_en",
]


def get_hito_by_tarea(cursor, tarea_id: int) -> dict | None:
    cursor.execute(
        """
        SELECT h.id, h.solicitud_id, t.id AS tarea_id, t.nombre AS tarea_nombre, h.nombre,
               h.descripcion, h.fecha_vencimiento, h.creado_en, h.creado_por,
               COALESCE(autor.nombre_completo, h.creado_por) AS creado_por_nombre, h.actualizado_en
        FROM hitos h
        JOIN tareas t ON t.hito_id = h.id
        LEFT JOIN miembros_equipo autor ON autor.usuario = h.creado_por
        WHERE t.id = %(tarea_id)s AND h.borrado_en IS NULL
        """,
        {"tarea_id": tarea_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(_COLUMNAS_HITO, row))


def list_hitos_by_solicitud(cursor, solicitud_id: int) -> list[dict]:
    """Para el detalle de solicitud (Fase 2 extra): todos los hitos de sus tareas, más
    recientes primero, con el nombre de la tarea dueña y el nombre del creador (se muestra
    como "responsable" del hito, ya que hitos no tiene columna de responsable propia)."""
    cursor.execute(
        """
        SELECT h.id, h.solicitud_id, t.id AS tarea_id, t.nombre AS tarea_nombre, h.nombre,
               h.descripcion, h.fecha_vencimiento, h.creado_en, h.creado_por,
               COALESCE(autor.nombre_completo, h.creado_por) AS creado_por_nombre, h.actualizado_en
        FROM hitos h
        LEFT JOIN tareas t ON t.hito_id = h.id
        LEFT JOIN miembros_equipo autor ON autor.usuario = h.creado_por
        WHERE h.solicitud_id = %(solicitud_id)s AND h.borrado_en IS NULL
        ORDER BY h.creado_en DESC
        """,
        {"solicitud_id": solicitud_id},
    )
    return [dict(zip(_COLUMNAS_HITO, row)) for row in cursor.fetchall()]


def insert_hito_para_tarea(
    cursor,
    tarea_id: int,
    solicitud_id: int,
    nombre: str,
    descripcion: str | None,
    fecha_vencimiento: date,
    actor: str,
) -> int:
    cursor.execute(
        """
        INSERT INTO hitos (solicitud_id, nombre, descripcion, fecha_vencimiento,
                            creado_en, creado_por, actualizado_en, actualizado_por)
        VALUES (%(solicitud_id)s, %(nombre)s, %(descripcion)s, %(fecha_vencimiento)s,
                now(), %(actor)s, now(), %(actor)s)
        RETURNING id
        """,
        {
            "solicitud_id": solicitud_id,
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_vencimiento": fecha_vencimiento,
            "actor": actor,
        },
    )
    hito_id = cursor.fetchone()[0]
    cursor.execute(
        "UPDATE tareas SET hito_id = %(hito_id)s WHERE id = %(tarea_id)s",
        {"hito_id": hito_id, "tarea_id": tarea_id},
    )
    return hito_id


def update_hito(
    cursor, hito_id: int, nombre: str, descripcion: str | None, fecha_vencimiento: date, actor: str
) -> int:
    cursor.execute(
        """
        UPDATE hitos
        SET nombre = %(nombre)s, descripcion = %(descripcion)s,
            fecha_vencimiento = %(fecha_vencimiento)s,
            actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s AND borrado_en IS NULL
        """,
        {
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_vencimiento": fecha_vencimiento,
            "id": hito_id,
            "actor": actor,
        },
    )
    return cursor.rowcount


def delete_hito(cursor, hito_id: int, actor: str) -> int:
    """Borrado lógico: tareas.hito_id se deja como está (sigue apuntando al hito, que
    ahora está marcado como borrado) — get_hito_by_tarea ya filtra borrado_en IS NULL, así
    que deja de mostrarse igual que si se hubiera desvinculado."""
    cursor.execute(
        "UPDATE hitos SET borrado_en = now(), borrado_por = %(actor)s WHERE id = %(id)s AND borrado_en IS NULL",
        {"actor": actor, "id": hito_id},
    )
    return cursor.rowcount


_COLUMNAS_COMENTARIO = [
    "id", "solicitud_id", "tarea_id", "tarea_nombre", "texto_comentario", "creado_en",
    "creado_por", "creado_por_nombre", "actualizado_en", "actualizado_por",
]


def list_comentarios_by_tarea(cursor, tarea_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT c.id, c.solicitud_id, c.tarea_id, t.nombre AS tarea_nombre, c.texto_comentario,
               c.creado_en, c.creado_por,
               COALESCE(autor.nombre_completo, c.creado_por) AS creado_por_nombre,
               c.actualizado_en, c.actualizado_por
        FROM comentarios c
        LEFT JOIN tareas t ON t.id = c.tarea_id
        LEFT JOIN miembros_equipo autor ON autor.usuario = c.creado_por
        WHERE c.tarea_id = %(tarea_id)s AND c.borrado_en IS NULL
        ORDER BY c.creado_en
        """,
        {"tarea_id": tarea_id},
    )
    return [dict(zip(_COLUMNAS_COMENTARIO, row)) for row in cursor.fetchall()]


def list_comentarios_by_solicitud(cursor, solicitud_id: int) -> list[dict]:
    """Para el detalle de solicitud (Fase 2 extra): todos los comentarios de sus tareas,
    más recientes primero, con el nombre de la tarea de origen y el nombre del autor."""
    cursor.execute(
        """
        SELECT c.id, c.solicitud_id, c.tarea_id, t.nombre AS tarea_nombre, c.texto_comentario,
               c.creado_en, c.creado_por,
               COALESCE(autor.nombre_completo, c.creado_por) AS creado_por_nombre,
               c.actualizado_en, c.actualizado_por
        FROM comentarios c
        LEFT JOIN tareas t ON t.id = c.tarea_id
        LEFT JOIN miembros_equipo autor ON autor.usuario = c.creado_por
        WHERE c.solicitud_id = %(solicitud_id)s AND c.borrado_en IS NULL
        ORDER BY c.creado_en DESC
        """,
        {"solicitud_id": solicitud_id},
    )
    return [dict(zip(_COLUMNAS_COMENTARIO, row)) for row in cursor.fetchall()]


def insert_comentario(cursor, solicitud_id: int, tarea_id: int | None, texto: str, actor: str) -> int:
    cursor.execute(
        """
        INSERT INTO comentarios (solicitud_id, tarea_id, texto_comentario,
                                  creado_en, creado_por, actualizado_en, actualizado_por)
        VALUES (%(solicitud_id)s, %(tarea_id)s, %(texto)s, now(), %(actor)s, now(), %(actor)s)
        RETURNING id
        """,
        {"solicitud_id": solicitud_id, "tarea_id": tarea_id, "texto": texto, "actor": actor},
    )
    return cursor.fetchone()[0]


def get_comentario_by_id(cursor, comentario_id: int) -> dict | None:
    cursor.execute(
        """
        SELECT c.id, c.solicitud_id, c.tarea_id, t.nombre AS tarea_nombre, c.texto_comentario,
               c.creado_en, c.creado_por,
               COALESCE(autor.nombre_completo, c.creado_por) AS creado_por_nombre,
               c.actualizado_en, c.actualizado_por
        FROM comentarios c
        LEFT JOIN tareas t ON t.id = c.tarea_id
        LEFT JOIN miembros_equipo autor ON autor.usuario = c.creado_por
        WHERE c.id = %(id)s AND c.borrado_en IS NULL
        """,
        {"id": comentario_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(_COLUMNAS_COMENTARIO, row))


def update_comentario(cursor, comentario_id: int, texto: str, actor: str) -> int:
    cursor.execute(
        """
        UPDATE comentarios
        SET texto_comentario = %(texto)s, actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s AND borrado_en IS NULL
        """,
        {"texto": texto, "id": comentario_id, "actor": actor},
    )
    return cursor.rowcount


def delete_comentario(cursor, comentario_id: int, actor: str) -> int:
    cursor.execute(
        "UPDATE comentarios SET borrado_en = now(), borrado_por = %(actor)s WHERE id = %(id)s AND borrado_en IS NULL",
        {"actor": actor, "id": comentario_id},
    )
    return cursor.rowcount


_COLUMNAS_ENLACE_TAREA = [
    "id", "solicitud_id", "tarea_id", "tarea_nombre", "tipo_enlace", "url", "aplicacion_id",
    "pagina_aplicacion", "descripcion", "creado_en", "creado_por", "creado_por_nombre",
    "actualizado_en", "actualizado_por",
]


def insert_enlace_tarea(
    cursor,
    tarea_id: int,
    solicitud_id: int,
    tipo_enlace: str,
    url: str | None,
    aplicacion_id: int | None,
    pagina_aplicacion: int | None,
    descripcion: str | None,
    actor: str,
) -> int:
    """enlaces_tarea no tiene borrado_en/borrado_por (a diferencia de comentarios/hitos):
    no forma parte del conjunto de entidades con borrado lógico auditado, es detalle interno
    de la tarea (mismo criterio ya aplicado en delete_tarea)."""
    cursor.execute(
        """
        INSERT INTO enlaces_tarea
            (solicitud_id, tarea_id, tipo_enlace, url, aplicacion_id, pagina_aplicacion,
             descripcion, creado_en, creado_por, actualizado_en, actualizado_por)
        VALUES
            (%(solicitud_id)s, %(tarea_id)s, %(tipo_enlace)s, %(url)s, %(aplicacion_id)s,
             %(pagina_aplicacion)s, %(descripcion)s, now(), %(actor)s, now(), %(actor)s)
        RETURNING id
        """,
        {
            "solicitud_id": solicitud_id,
            "tarea_id": tarea_id,
            "tipo_enlace": tipo_enlace,
            "url": url,
            "aplicacion_id": aplicacion_id,
            "pagina_aplicacion": pagina_aplicacion,
            "descripcion": descripcion,
            "actor": actor,
        },
    )
    return cursor.fetchone()[0]


def get_enlace_tarea_by_id(cursor, enlace_id: int) -> dict | None:
    cursor.execute(
        """
        SELECT e.id, e.solicitud_id, e.tarea_id, t.nombre AS tarea_nombre, e.tipo_enlace,
               e.url, e.aplicacion_id, e.pagina_aplicacion, e.descripcion, e.creado_en,
               e.creado_por, COALESCE(autor.nombre_completo, e.creado_por) AS creado_por_nombre,
               e.actualizado_en, e.actualizado_por
        FROM enlaces_tarea e
        LEFT JOIN tareas t ON t.id = e.tarea_id
        LEFT JOIN miembros_equipo autor ON autor.usuario = e.creado_por
        WHERE e.id = %(id)s
        """,
        {"id": enlace_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(_COLUMNAS_ENLACE_TAREA, row))


def list_enlaces_by_tarea(cursor, tarea_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT e.id, e.solicitud_id, e.tarea_id, t.nombre AS tarea_nombre, e.tipo_enlace,
               e.url, e.aplicacion_id, e.pagina_aplicacion, e.descripcion, e.creado_en,
               e.creado_por, COALESCE(autor.nombre_completo, e.creado_por) AS creado_por_nombre,
               e.actualizado_en, e.actualizado_por
        FROM enlaces_tarea e
        LEFT JOIN tareas t ON t.id = e.tarea_id
        LEFT JOIN miembros_equipo autor ON autor.usuario = e.creado_por
        WHERE e.tarea_id = %(tarea_id)s
        ORDER BY e.creado_en
        """,
        {"tarea_id": tarea_id},
    )
    return [dict(zip(_COLUMNAS_ENLACE_TAREA, row)) for row in cursor.fetchall()]


def list_enlaces_by_solicitud(cursor, solicitud_id: int) -> list[dict]:
    """Para el detalle de solicitud (Fase 2 extra): todos los enlaces de las tareas de esta
    solicitud, más recientes primero, con el nombre de la tarea dueña y el nombre del autor."""
    cursor.execute(
        """
        SELECT e.id, e.solicitud_id, e.tarea_id, t.nombre AS tarea_nombre, e.tipo_enlace,
               e.url, e.aplicacion_id, e.pagina_aplicacion, e.descripcion, e.creado_en,
               e.creado_por, COALESCE(autor.nombre_completo, e.creado_por) AS creado_por_nombre,
               e.actualizado_en, e.actualizado_por
        FROM enlaces_tarea e
        LEFT JOIN tareas t ON t.id = e.tarea_id
        LEFT JOIN miembros_equipo autor ON autor.usuario = e.creado_por
        WHERE e.solicitud_id = %(solicitud_id)s
        ORDER BY e.creado_en DESC
        """,
        {"solicitud_id": solicitud_id},
    )
    return [dict(zip(_COLUMNAS_ENLACE_TAREA, row)) for row in cursor.fetchall()]


_COLUMNAS_POR_HACER = [
    "id", "solicitud_id", "tarea_id", "tarea_nombre", "responsable_id", "responsable",
    "nombre", "descripcion", "esta_completa",
    "creado_en", "creado_por", "creado_por_nombre", "actualizado_en", "actualizado_por",
]

_SELECT_POR_HACER = """
    SELECT p.id, p.solicitud_id, p.tarea_id, t.nombre AS tarea_nombre,
           p.responsable_id, resp.nombre_completo AS responsable,
           p.nombre, p.descripcion,
           CASE WHEN p.esta_completa = 'Y' THEN true ELSE false END AS esta_completa,
           p.creado_en, p.creado_por,
           COALESCE(autor.nombre_completo, p.creado_por) AS creado_por_nombre,
           p.actualizado_en, p.actualizado_por
    FROM tarea_por_hacer p
    LEFT JOIN tareas t ON t.id = p.tarea_id
    LEFT JOIN miembros_equipo resp ON resp.id = p.responsable_id
    LEFT JOIN miembros_equipo autor ON autor.usuario = p.creado_por
"""


def list_por_hacer_by_tarea(cursor, tarea_id: int) -> list[dict]:
    """tarea_por_hacer no tiene borrado_en/borrado_por (mismo criterio que enlaces_tarea:
    detalle interno de la tarea, sin borrado lógico auditado; ver delete_tarea)."""
    cursor.execute(
        _SELECT_POR_HACER + " WHERE p.tarea_id = %(tarea_id)s ORDER BY p.creado_en",
        {"tarea_id": tarea_id},
    )
    return [dict(zip(_COLUMNAS_POR_HACER, row)) for row in cursor.fetchall()]


def insert_por_hacer(
    cursor,
    tarea_id: int,
    solicitud_id: int,
    nombre: str,
    descripcion: str | None,
    responsable_id: int | None,
    actor: str,
) -> int:
    """Un ítem nuevo siempre arranca incompleto ('N') — esta_completa no es un campo de
    creación, se marca después con el PUT."""
    cursor.execute(
        """
        INSERT INTO tarea_por_hacer
            (solicitud_id, tarea_id, responsable_id, nombre, descripcion, esta_completa,
             creado_en, creado_por, actualizado_en, actualizado_por)
        VALUES
            (%(solicitud_id)s, %(tarea_id)s, %(responsable_id)s, %(nombre)s, %(descripcion)s, 'N',
             now(), %(actor)s, now(), %(actor)s)
        RETURNING id
        """,
        {
            "solicitud_id": solicitud_id,
            "tarea_id": tarea_id,
            "responsable_id": responsable_id,
            "nombre": nombre,
            "descripcion": descripcion,
            "actor": actor,
        },
    )
    return cursor.fetchone()[0]


def get_por_hacer_by_id(cursor, item_id: int) -> dict | None:
    cursor.execute(_SELECT_POR_HACER + " WHERE p.id = %(id)s", {"id": item_id})
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(_COLUMNAS_POR_HACER, row))


def update_por_hacer(
    cursor,
    item_id: int,
    nombre: str,
    descripcion: str | None,
    responsable_id: int | None,
    esta_completa: bool,
    actor: str,
) -> int:
    """Reemplazo total (igual que update_comentario/update_hito, no COALESCE): el
    formulario de edición y el toggle rápido de completado usan este mismo UPDATE,
    siempre enviando el ítem completo."""
    cursor.execute(
        """
        UPDATE tarea_por_hacer
        SET nombre = %(nombre)s, descripcion = %(descripcion)s,
            responsable_id = %(responsable_id)s, esta_completa = %(esta_completa)s,
            actualizado_en = now(), actualizado_por = %(actor)s
        WHERE id = %(id)s
        """,
        {
            "nombre": nombre,
            "descripcion": descripcion,
            "responsable_id": responsable_id,
            "esta_completa": "Y" if esta_completa else "N",
            "id": item_id,
            "actor": actor,
        },
    )
    return cursor.rowcount


def delete_por_hacer(cursor, item_id: int) -> int:
    """Borrado físico real: tarea_por_hacer no tiene columnas de auditoría de borrado."""
    cursor.execute("DELETE FROM tarea_por_hacer WHERE id = %(id)s", {"id": item_id})
    return cursor.rowcount


_ORDEN_SOLICITUDES = {
    # orden_visualizacion/orden ya existen en los catálogos para reflejar el flujo de
    # negocio (p. ej. estatus va En espera → Planeado → ... → Completado/Cancelado), no
    # el alfabético — se reutilizan aquí en vez de ordenar por texto.
    "estatus": "e.orden_visualizacion NULLS LAST, s.creado_en DESC",
    "tipo": "t.orden NULLS LAST, t.tipo NULLS LAST, s.creado_en DESC",
    "cliente": "c.nombre NULLS LAST, s.creado_en DESC",
    # orden_prioridad es un entero validado 1-5 desde la Fase 1.17 (antes era varchar libre).
    "prioridad": "s.orden_prioridad, s.creado_en DESC",
}


def list_solicitudes(
    cursor,
    cliente: str | None = None,
    nombre: str | None = None,
    estatus: str | None = None,
    area: str | None = None,
    orden_por: str | None = None,
    involucrado_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """Listado para la página de Solicitudes (Fase 1.6). Trae nombres legibles de los
    catálogos (no solo ids) vía LEFT JOIN. Por default, más recientes primero; `orden_por`
    permite ordenar por estatus/tipo/cliente/prioridad (ver _ORDEN_SOLICITUDES).
    `involucrado_id` (Fase 1.19) filtra a las solicitudes donde ese miembro participa: como
    solicitante, como responsable de atención, o como responsable de alguna de sus tareas.
    `area` (Punto 3, 2026-09-04) filtra por el área/perfil del responsable de atención (mismo
    campo `miembros_equipo.perfil` que ya usa Dirección General)."""
    condiciones = ["s.borrado_en IS NULL"]
    parametros: dict = {"max_rows": limit}
    if cliente:
        condiciones.append("c.nombre ILIKE %(cliente)s")
        parametros["cliente"] = f"%{cliente}%"
    if nombre:
        condiciones.append("s.nombre ILIKE %(nombre)s")
        parametros["nombre"] = f"%{nombre}%"
    if estatus:
        condiciones.append("s.codigo_estatus = %(estatus)s")
        parametros["estatus"] = estatus
    if area:
        condiciones.append("coalesce(ra.perfil, 'Sin área') ILIKE %(area)s")
        parametros["area"] = f"%{area}%"
    if involucrado_id:
        condiciones.append(
            "(s.solicitante = %(involucrado_id)s OR s.responsable_atencion_id = %(involucrado_id)s "
            "OR EXISTS (SELECT 1 FROM tareas ti WHERE ti.solicitud_id = s.id "
            "AND ti.responsable_id = %(involucrado_id)s AND ti.borrado_en IS NULL))"
        )
        parametros["involucrado_id"] = involucrado_id

    where = f"WHERE {' AND '.join(condiciones)}"
    order_by = _ORDEN_SOLICITUDES.get(orden_por or "", "s.creado_en DESC")
    cursor.execute(
        f"""
        SELECT s.id, s.nombre, c.nombre AS cliente, t.tipo AS tipo,
               s.codigo_estatus, e.descripcion AS estatus_descripcion,
               m.nombre_completo AS solicitante, s.orden_prioridad,
               s.fecha_entrega, ra.nombre_completo AS responsable_atencion,
               coalesce(ra.perfil, 'Sin área') AS responsable_atencion_area, s.creado_en
        FROM solicitudes s
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN tipos_solicitud t ON t.id = s.tipo
        LEFT JOIN estatus e ON e.codigo = s.codigo_estatus
        LEFT JOIN miembros_equipo m ON m.id = s.solicitante
        LEFT JOIN miembros_equipo ra ON ra.id = s.responsable_atencion_id
        {where}
        ORDER BY {order_by}
        LIMIT %(max_rows)s
        """,
        parametros,
    )
    columnas = [
        "id", "nombre", "cliente", "tipo", "codigo_estatus", "estatus_descripcion",
        "solicitante", "orden_prioridad", "fecha_entrega", "responsable_atencion",
        "responsable_atencion_area", "creado_en",
    ]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------------
# Notificaciones (Fase 1.20)
# ---------------------------------------------------------------------------------


def find_miembro_activo_by_usuario(cursor, usuario: str, excluir_externos: bool = False) -> dict | None:
    """Resuelve una mención @usuario en un comentario: solo miembros con acceso activo (no
    tiene sentido notificar a alguien dado de baja o sin acceso). `excluir_externos` (Punto 6,
    2026-09-04): a nivel tarea un Externo nunca puede ser mencionado, solo a nivel solicitud."""
    condicion_externo = "AND codigo_rol_scrum != 'EXTERNO'" if excluir_externos else ""
    cursor.execute(
        f"""
        SELECT id, nombre_completo
        FROM miembros_equipo
        WHERE usuario ILIKE %(usuario)s AND acceso_activo = true AND borrado_en IS NULL
        {condicion_externo}
        """,
        {"usuario": usuario},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {"id": row[0], "nombre_completo": row[1]}


def list_miembros_activos_ids(cursor, excluir_externos: bool = False) -> list[int]:
    """Usado para "@todos": todos los miembros con acceso activo. `excluir_externos` (Punto 6,
    2026-09-04): a nivel tarea "@todos" nunca debe incluir a los Externos."""
    condicion_externo = "AND codigo_rol_scrum != 'EXTERNO'" if excluir_externos else ""
    cursor.execute(
        f"SELECT id FROM miembros_equipo WHERE acceso_activo = true AND borrado_en IS NULL {condicion_externo}"
    )
    return [row[0] for row in cursor.fetchall()]


def insert_notificacion(
    cursor,
    destinatario_id: int,
    tipo: str,
    mensaje: str,
    entidad_tipo: str | None = None,
    entidad_id: int | None = None,
) -> int:
    cursor.execute(
        """
        INSERT INTO notificaciones (destinatario_id, tipo, mensaje, entidad_tipo, entidad_id)
        VALUES (%(destinatario_id)s, %(tipo)s, %(mensaje)s, %(entidad_tipo)s, %(entidad_id)s)
        RETURNING id
        """,
        {
            "destinatario_id": destinatario_id,
            "tipo": tipo,
            "mensaje": mensaje,
            "entidad_tipo": entidad_tipo,
            "entidad_id": entidad_id,
        },
    )
    return cursor.fetchone()[0]


def list_notificaciones_by_destinatario(
    cursor, miembro_id: int, solo_no_leidas: bool = False, limit: int = 50
) -> list[dict]:
    condiciones = ["destinatario_id = %(miembro_id)s"]
    if solo_no_leidas:
        condiciones.append("leido_en IS NULL")
    where = " AND ".join(condiciones)
    cursor.execute(
        f"""
        SELECT id, tipo, mensaje, entidad_tipo, entidad_id, leido_en, creado_en
        FROM notificaciones
        WHERE {where}
        ORDER BY creado_en DESC
        LIMIT %(limit)s
        """,
        {"miembro_id": miembro_id, "limit": limit},
    )
    columnas = ["id", "tipo", "mensaje", "entidad_tipo", "entidad_id", "leido_en", "creado_en"]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def count_no_leidas(cursor, miembro_id: int) -> int:
    cursor.execute(
        "SELECT count(*) FROM notificaciones WHERE destinatario_id = %(miembro_id)s AND leido_en IS NULL",
        {"miembro_id": miembro_id},
    )
    return cursor.fetchone()[0]


def marcar_notificacion_leida(cursor, notificacion_id: int, miembro_id: int) -> int:
    """Solo el propio destinatario puede marcarla leída (WHERE destinatario_id = miembro_id),
    para no exponer un endpoint que permita marcar notificaciones ajenas."""
    cursor.execute(
        """
        UPDATE notificaciones SET leido_en = now()
        WHERE id = %(id)s AND destinatario_id = %(miembro_id)s AND leido_en IS NULL
        """,
        {"id": notificacion_id, "miembro_id": miembro_id},
    )
    return cursor.rowcount


def marcar_todas_notificaciones_leidas(cursor, miembro_id: int) -> int:
    cursor.execute(
        "UPDATE notificaciones SET leido_en = now() WHERE destinatario_id = %(miembro_id)s AND leido_en IS NULL",
        {"miembro_id": miembro_id},
    )
    return cursor.rowcount


# Fase de dashboard de Inicio: no hay catálogo de prioridad en BD (son 5 niveles fijos, Fase
# 1.17), así que el zero-fill de los 5 niveles se arma en Python en vez de con un LEFT JOIN.
PRIORIDAD_DESCRIPCIONES = {1: "Crítica", 2: "Alta", 3: "Media", 4: "Baja", 5: "Trivial"}


def get_resumen_solicitudes(
    cursor, *, solicitante_id: int | None = None, responsable_atencion_id: int | None = None
) -> dict:
    """Resumen para el dashboard de Inicio: total, desglose por estatus y por prioridad de las
    solicitudes activas, opcionalmente filtradas por quién es el solicitante o el responsable de
    atención. El filtro va dentro del ON del LEFT JOIN de estatus (no en el WHERE) para no perder
    el zero-fill de los estatus sin solicitudes."""
    cursor.execute(
        """
        SELECT e.codigo, e.descripcion, count(s.id) AS total
        FROM estatus e
        LEFT JOIN solicitudes s ON s.codigo_estatus = e.codigo AND s.borrado_en IS NULL
            AND (%(solicitante_id)s::bigint IS NULL OR s.solicitante = %(solicitante_id)s::bigint)
            AND (
                %(responsable_atencion_id)s::bigint IS NULL
                OR s.responsable_atencion_id = %(responsable_atencion_id)s::bigint
            )
        GROUP BY e.codigo, e.descripcion, e.orden_visualizacion
        ORDER BY e.orden_visualizacion
        """,
        {"solicitante_id": solicitante_id, "responsable_atencion_id": responsable_atencion_id},
    )
    por_estatus = [{"valor": row[0], "descripcion": row[1], "total": row[2]} for row in cursor.fetchall()]

    condiciones = ["s.borrado_en IS NULL"]
    parametros: dict = {}
    if solicitante_id is not None:
        condiciones.append("s.solicitante = %(solicitante_id)s")
        parametros["solicitante_id"] = solicitante_id
    if responsable_atencion_id is not None:
        condiciones.append("s.responsable_atencion_id = %(responsable_atencion_id)s")
        parametros["responsable_atencion_id"] = responsable_atencion_id
    cursor.execute(
        f"""
        SELECT s.orden_prioridad, count(*) AS total
        FROM solicitudes s
        WHERE {' AND '.join(condiciones)}
        GROUP BY s.orden_prioridad
        """,
        parametros,
    )
    conteos_prioridad = {row[0]: row[1] for row in cursor.fetchall()}
    por_prioridad = [
        {"valor": str(nivel), "descripcion": PRIORIDAD_DESCRIPCIONES[nivel], "total": conteos_prioridad.get(nivel, 0)}
        for nivel in range(1, 6)
    ]

    return {
        "total": sum(fila["total"] for fila in por_estatus),
        "por_estatus": por_estatus,
        "por_prioridad": por_prioridad,
    }


def get_resumen_tareas(cursor, *, responsable_id: int | None = None) -> dict:
    """Resumen para el dashboard de Inicio: total, desglose por estatus de tarea y por
    prioridad heredada de la solicitud, opcionalmente filtrado por responsable de la tarea."""
    cursor.execute(
        """
        SELECT et.codigo, et.descripcion, count(t.id) AS total
        FROM estatus_tarea et
        LEFT JOIN tareas t ON t.codigo_estatus_tarea = et.codigo AND t.borrado_en IS NULL
            AND (%(responsable_id)s::bigint IS NULL OR t.responsable_id = %(responsable_id)s::bigint)
        GROUP BY et.codigo, et.descripcion, et.orden_visualizacion
        ORDER BY et.orden_visualizacion
        """,
        {"responsable_id": responsable_id},
    )
    por_estatus = [{"valor": row[0], "descripcion": row[1], "total": row[2]} for row in cursor.fetchall()]

    condiciones = ["t.borrado_en IS NULL"]
    parametros: dict = {}
    if responsable_id is not None:
        condiciones.append("t.responsable_id = %(responsable_id)s")
        parametros["responsable_id"] = responsable_id
    cursor.execute(
        f"""
        SELECT s.orden_prioridad, count(*) AS total
        FROM tareas t
        JOIN solicitudes s ON s.id = t.solicitud_id
        WHERE {' AND '.join(condiciones)}
        GROUP BY s.orden_prioridad
        """,
        parametros,
    )
    conteos_prioridad = {row[0]: row[1] for row in cursor.fetchall()}
    por_prioridad = [
        {"valor": str(nivel), "descripcion": PRIORIDAD_DESCRIPCIONES[nivel], "total": conteos_prioridad.get(nivel, 0)}
        for nivel in range(1, 6)
    ]

    return {
        "total": sum(fila["total"] for fila in por_estatus),
        "por_estatus": por_estatus,
        "por_prioridad": por_prioridad,
    }

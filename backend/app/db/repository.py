from __future__ import annotations

import logging
from datetime import date

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
             orden_prioridad, creado_en, creado_por, actualizado_en, actualizado_por)
        VALUES
            (%(nombre)s, %(descripcion)s, %(solicitante)s, %(cliente)s, %(tipo)s,
             %(codigo_estatus)s, %(canal)s, %(orden_prioridad)s, now(), %(actor)s,
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


def mark_email_processed(cursor, message_id: str, id_solicitud: int | None) -> None:
    cursor.execute(
        "INSERT INTO emails_procesados (email_message_id, solicitud_id) VALUES (%(message_id)s, %(id_solicitud)s)",
        {"message_id": message_id, "id_solicitud": id_solicitud},
    )


def list_miembros(cursor) -> list[dict]:
    cursor.execute(
        "SELECT id, nombre_completo, correo_electronico FROM miembros_equipo ORDER BY nombre_completo"
    )
    return [
        {"id": row[0], "nombre_completo": row[1], "correo_electronico": row[2]}
        for row in cursor.fetchall()
    ]


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
        SELECT m.id, m.usuario, m.nombre_completo, m.codigo_rol_scrum,
               r.descripcion AS rol_scrum_descripcion, m.acceso_activo
        FROM miembros_equipo m
        LEFT JOIN roles_scrum r ON r.codigo = m.codigo_rol_scrum
        ORDER BY m.nombre_completo
        """
    )
    columnas = ["id", "usuario", "nombre_completo", "codigo_rol_scrum", "rol_scrum_descripcion", "acceso_activo"]
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


def actualizar_acceso_miembro(
    cursor,
    miembro_id: int,
    codigo_rol_scrum: str | None,
    acceso_activo: bool | None,
    password_hash: str | None,
) -> int:
    """Todos los campos son opcionales (solo se actualiza lo que no sea None) — el mismo
    endpoint sirve para cambiar rol, activar/desactivar, y/o resetear la contraseña. Igual
    que en otorgar_acceso_miembro, si viene password_hash (el Scrum Master reseteó la
    contraseña de alguien) se fuerza debe_cambiar_password."""
    cursor.execute(
        """
        UPDATE miembros_equipo
        SET codigo_rol_scrum = COALESCE(%(codigo_rol_scrum)s, codigo_rol_scrum),
            acceso_activo = COALESCE(%(acceso_activo)s, acceso_activo),
            password_hash = COALESCE(%(password_hash)s, password_hash),
            debe_cambiar_password = CASE
                WHEN %(password_hash)s IS NOT NULL THEN true
                ELSE debe_cambiar_password
            END,
            actualizado_en = now(), actualizado_por = current_user
        WHERE id = %(id)s
        """,
        {
            "codigo_rol_scrum": codigo_rol_scrum,
            "acceso_activo": acceso_activo,
            "password_hash": password_hash,
            "id": miembro_id,
        },
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
               s.orden_prioridad, cs.canal AS canal, s.canal AS canal_id,
               s.fecha_completado, s.creado_en, s.actualizado_en, s.actualizado_por
        FROM solicitudes s
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN tipos_solicitud t ON t.id = s.tipo
        LEFT JOIN estatus e ON e.codigo = s.codigo_estatus
        LEFT JOIN miembros_equipo m ON m.id = s.solicitante
        LEFT JOIN canales_solicitud cs ON cs.id = s.canal
        WHERE s.id = %(id)s AND s.borrado_en IS NULL
        """,
        {"id": solicitud_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = [
        "id", "nombre", "descripcion", "cliente", "cliente_id", "tipo", "tipo_id",
        "codigo_estatus", "estatus_descripcion", "solicitante", "orden_prioridad",
        "canal", "canal_id", "fecha_completado", "creado_en", "actualizado_en", "actualizado_por",
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
    orden_prioridad: str | None,
    fecha_completado,
    actor: str,
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
            actualizado_en = now(), actualizado_por = %(actor)s
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
            "id": solicitud_id,
            "actor": actor,
        },
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
               t.codigo_estatus_tarea, et.descripcion AS estatus_tarea_descripcion,
               t.fecha_inicio, t.fecha_fin, t.horas_estimadas, t.horas_reales,
               t.creado_en, t.actualizado_en
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
        "responsable_id", "responsable", "codigo_estatus_tarea", "estatus_tarea_descripcion",
        "fecha_inicio", "fecha_fin", "horas_estimadas", "horas_reales", "creado_en", "actualizado_en",
    ]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def list_tareas_by_solicitud(cursor, solicitud_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT t.id, t.solicitud_id, t.nombre, t.descripcion, t.responsable_id,
               m.nombre_completo AS responsable, t.codigo_estatus_tarea,
               et.descripcion AS estatus_tarea_descripcion, t.fecha_inicio,
               t.fecha_fin, t.horas_estimadas, t.horas_reales, t.creado_en, t.actualizado_en
        FROM tareas t
        LEFT JOIN miembros_equipo m ON m.id = t.responsable_id
        LEFT JOIN estatus_tarea et ON et.codigo = t.codigo_estatus_tarea
        WHERE t.solicitud_id = %(id)s AND t.borrado_en IS NULL
        ORDER BY t.creado_en
        """,
        {"id": solicitud_id},
    )
    columnas = [
        "id", "solicitud_id", "nombre", "descripcion", "responsable_id", "responsable",
        "codigo_estatus_tarea", "estatus_tarea_descripcion", "fecha_inicio", "fecha_fin",
        "horas_estimadas", "horas_reales", "creado_en", "actualizado_en",
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
    horas_estimadas: int | None = None,
    horas_reales: int | None = None,
) -> int:
    """fecha_inicio/fecha_fin son NOT NULL: si el formulario no los captura, se
    inicializan en el backend (hoy / hoy + 7 días)."""
    cursor.execute(
        """
        INSERT INTO tareas
            (solicitud_id, nombre, descripcion, responsable_id, codigo_estatus_tarea,
             fecha_inicio, fecha_fin, horas_estimadas, horas_reales,
             creado_en, creado_por, actualizado_en, actualizado_por)
        VALUES
            (%(solicitud_id)s, %(nombre)s, %(descripcion)s, %(responsable_id)s, %(codigo_estatus_tarea)s,
             COALESCE(%(fecha_inicio)s, now()::date),
             COALESCE(%(fecha_fin)s, (now() + interval '7 days')::date),
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
    horas_estimadas: int | None = None,
    horas_reales: int | None = None,
) -> int:
    """fecha_inicio/fecha_fin son NOT NULL: si no se envían, se conserva el valor actual
    (COALESCE) en vez de fallar. horas_estimadas/horas_reales sí son nullable: se
    sobrescriben tal cual, incluyendo a NULL si el formulario los deja vacíos."""
    cursor.execute(
        """
        UPDATE tareas
        SET nombre = %(nombre)s, descripcion = %(descripcion)s,
            responsable_id = %(responsable_id)s, codigo_estatus_tarea = %(codigo_estatus_tarea)s,
            fecha_inicio = COALESCE(%(fecha_inicio)s, fecha_inicio),
            fecha_fin = COALESCE(%(fecha_fin)s, fecha_fin),
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
               m.nombre_completo AS responsable, t.codigo_estatus_tarea,
               et.descripcion AS estatus_tarea_descripcion, t.fecha_inicio,
               t.fecha_fin, t.horas_estimadas, t.horas_reales, t.creado_en, t.actualizado_en
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
        "responsable_id", "responsable", "codigo_estatus_tarea", "estatus_tarea_descripcion",
        "fecha_inicio", "fecha_fin", "horas_estimadas", "horas_reales", "creado_en", "actualizado_en",
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


def get_hito_by_tarea(cursor, tarea_id: int) -> dict | None:
    cursor.execute(
        """
        SELECT h.id, h.solicitud_id, h.nombre, h.descripcion, h.fecha_vencimiento,
               h.creado_en, h.actualizado_en
        FROM hitos h
        JOIN tareas t ON t.hito_id = h.id
        WHERE t.id = %(tarea_id)s AND h.borrado_en IS NULL
        """,
        {"tarea_id": tarea_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = ["id", "solicitud_id", "nombre", "descripcion", "fecha_vencimiento", "creado_en", "actualizado_en"]
    return dict(zip(columnas, row))


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


def list_comentarios_by_tarea(cursor, tarea_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT id, solicitud_id, tarea_id, texto_comentario, creado_en, creado_por,
               actualizado_en, actualizado_por
        FROM comentarios
        WHERE tarea_id = %(tarea_id)s AND borrado_en IS NULL
        ORDER BY creado_en
        """,
        {"tarea_id": tarea_id},
    )
    columnas = [
        "id", "solicitud_id", "tarea_id", "texto_comentario", "creado_en", "creado_por",
        "actualizado_en", "actualizado_por",
    ]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


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
        SELECT id, solicitud_id, tarea_id, texto_comentario, creado_en, creado_por,
               actualizado_en, actualizado_por
        FROM comentarios
        WHERE id = %(id)s AND borrado_en IS NULL
        """,
        {"id": comentario_id},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columnas = [
        "id", "solicitud_id", "tarea_id", "texto_comentario", "creado_en", "creado_por",
        "actualizado_en", "actualizado_por",
    ]
    return dict(zip(columnas, row))


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


_ORDEN_SOLICITUDES = {
    # orden_visualizacion/orden ya existen en los catálogos para reflejar el flujo de
    # negocio (p. ej. estatus va En espera → Planeado → ... → Completado/Cancelado), no
    # el alfabético — se reutilizan aquí en vez de ordenar por texto.
    "estatus": "e.orden_visualizacion NULLS LAST, s.creado_en DESC",
    "tipo": "t.orden NULLS LAST, t.tipo NULLS LAST, s.creado_en DESC",
    "cliente": "c.nombre NULLS LAST, s.creado_en DESC",
    # orden_prioridad es un varchar libre (no un catálogo); se castea a entero solo cuando
    # el valor es puramente numérico para poder ordenar 1 < 2 < 10 en vez de alfabético
    # ("1" < "10" < "2"), sin que un valor no numérico futuro rompa la consulta.
    "prioridad": (
        "CASE WHEN s.orden_prioridad ~ '^[0-9]+$' THEN s.orden_prioridad::int END NULLS LAST, "
        "s.creado_en DESC"
    ),
}


def list_solicitudes(
    cursor,
    cliente: str | None = None,
    nombre: str | None = None,
    estatus: str | None = None,
    orden_por: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Listado para la página de Solicitudes (Fase 1.6). Trae nombres legibles de los
    catálogos (no solo ids) vía LEFT JOIN. Por default, más recientes primero; `orden_por`
    permite ordenar por estatus/tipo/cliente/prioridad (ver _ORDEN_SOLICITUDES)."""
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

    where = f"WHERE {' AND '.join(condiciones)}"
    order_by = _ORDEN_SOLICITUDES.get(orden_por or "", "s.creado_en DESC")
    cursor.execute(
        f"""
        SELECT s.id, s.nombre, c.nombre AS cliente, t.tipo AS tipo,
               s.codigo_estatus, e.descripcion AS estatus_descripcion,
               m.nombre_completo AS solicitante, s.orden_prioridad, s.creado_en
        FROM solicitudes s
        LEFT JOIN clientes c ON c.id = s.cliente
        LEFT JOIN tipos_solicitud t ON t.id = s.tipo
        LEFT JOIN estatus e ON e.codigo = s.codigo_estatus
        LEFT JOIN miembros_equipo m ON m.id = s.solicitante
        {where}
        ORDER BY {order_by}
        LIMIT %(max_rows)s
        """,
        parametros,
    )
    columnas = [
        "id", "nombre", "cliente", "tipo", "codigo_estatus", "estatus_descripcion",
        "solicitante", "orden_prioridad", "creado_en",
    ]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]

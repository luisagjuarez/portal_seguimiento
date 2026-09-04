from __future__ import annotations

import re

from app.db import repository

# Compartido entre routes_tareas.py (comentarios de tarea) y routes_solicitudes.py (comentarios
# de solicitud, Punto 6, 2026-09-04): @usuario notifica a ese miembro (si tiene acceso activo);
# @todos notifica a todo el equipo con acceso activo. No se notifica dos veces al mismo
# destinatario, incluido quien escribió el comentario si se menciona a sí mismo.
_PATRON_MENCION = re.compile(r"@(\w+)")


def resolver_destinatarios_mencion(cursor, texto: str, *, excluir_externos: bool = False) -> set[int]:
    """`excluir_externos` controla si se puede arrobar a un Externo por @usuario directo: True a
    nivel tarea (nunca), False a nivel solicitud (sí). `@todos` siempre significa "todo el
    equipo interno" sin importar ese flag — nunca debe terminar notificando a un cliente
    Externo solo por estar activo, ni siquiera desde un comentario de solicitud."""
    tokens = {m.group(1) for m in _PATRON_MENCION.finditer(texto)}
    if not tokens:
        return set()

    destinatarios_ids: set[int] = set()
    for token in tokens:
        if token.upper() == "TODOS":
            destinatarios_ids.update(repository.list_miembros_activos_ids(cursor, excluir_externos=True))
            continue
        miembro = repository.find_miembro_activo_by_usuario(cursor, token, excluir_externos=excluir_externos)
        if miembro:
            destinatarios_ids.add(miembro["id"])
    return destinatarios_ids

-- Alta/baja/actualización de miembros_equipo desde el módulo de Usuarios (Fase 1.10):
-- borrado lógico igual que solicitudes/tareas/comentarios/hitos, y unicidad real de
-- usuario/correo ahora que el alta se hace desde la app (antes solo se poblaba por seed).

ALTER TABLE miembros_equipo
    ADD COLUMN borrado_en  timestamptz,
    ADD COLUMN borrado_por varchar(255);

-- Case-insensitive (las búsquedas de login/duplicados usan ILIKE) y solo entre miembros
-- activos: un usuario/correo dado de baja puede reutilizarse para un alta nueva.
CREATE UNIQUE INDEX ux_miembros_equipo_usuario_activo
    ON miembros_equipo (UPPER(usuario)) WHERE borrado_en IS NULL;

CREATE UNIQUE INDEX ux_miembros_equipo_correo_activo
    ON miembros_equipo (UPPER(correo_electronico))
    WHERE correo_electronico IS NOT NULL AND borrado_en IS NULL;

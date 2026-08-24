-- Catálogo de estatus de tarea (estilo Scrum/Kanban), reemplaza el binario
-- tareas.esta_completa ('Y'/'N'). Mismo patrón que la tabla estatus (solicitudes).

CREATE TABLE estatus_tarea (
    codigo               varchar(20) NOT NULL,
    descripcion          varchar(255) NOT NULL,
    orden_visualizacion  integer NOT NULL,
    creado_en            timestamptz NOT NULL DEFAULT now(),
    creado_por           varchar(255) NOT NULL DEFAULT current_user,
    actualizado_en       timestamptz NOT NULL DEFAULT now(),
    actualizado_por      varchar(255) NOT NULL DEFAULT current_user,
    CONSTRAINT estatus_tarea_pk PRIMARY KEY (codigo)
);

INSERT INTO estatus_tarea (codigo, descripcion, orden_visualizacion) VALUES
    ('POR HACER',    'Por hacer',     1),
    ('EN PROGRESO',  'En progreso',   2),
    ('EN REVISION',  'En revisión',   3),
    ('COMPLETADO',   'Completado',    4);

ALTER TABLE tareas ADD COLUMN codigo_estatus_tarea varchar(20);

UPDATE tareas SET codigo_estatus_tarea = CASE esta_completa
    WHEN 'Y' THEN 'COMPLETADO'
    ELSE 'POR HACER'
END;

-- Verificación manual antes de continuar (debe dar 0 filas):
-- SELECT COUNT(*) FROM tareas WHERE codigo_estatus_tarea IS NULL;

ALTER TABLE tareas ALTER COLUMN codigo_estatus_tarea SET NOT NULL;

ALTER TABLE tareas
    ADD CONSTRAINT fk_tareas_estatus_tarea
    FOREIGN KEY (codigo_estatus_tarea) REFERENCES estatus_tarea(codigo);

ALTER TABLE tareas DROP COLUMN esta_completa;

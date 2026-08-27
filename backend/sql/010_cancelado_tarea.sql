-- Agrega el estatus "Cancelado" a tareas, que hasta ahora solo existía para solicitudes.
-- Necesario para que el equipo (no Scrum Master) pueda cancelar una tarea en vez de borrarla.

INSERT INTO estatus_tarea (codigo, descripcion, orden_visualizacion) VALUES
    ('CANCELADO', 'Cancelado', 5);

-- Vista "Carga del equipo": marca de estado para no repetir la notificación de "sin tarea
-- en progreso" cada vez que corre el chequeo periódico (cada 10 min) mientras la condición
-- siga siendo la misma. Se borra la fila cuando el miembro vuelve a tener una tarea En progreso,
-- permitiendo notificar de nuevo si en el futuro se vuelve a quedar sin nada.

CREATE TABLE alertas_sin_tarea_activa (
    miembro_id    bigint NOT NULL REFERENCES miembros_equipo(id),
    notificado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT alertas_sin_tarea_activa_pk PRIMARY KEY (miembro_id)
);

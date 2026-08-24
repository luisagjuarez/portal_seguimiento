-- Permite que un comentario se relacione directamente con una tarea (además de con una
-- solicitud, como ya hacía). solicitud_id sigue NOT NULL: se deriva automáticamente del
-- solicitud_id de la tarea al crear un comentario de tarea, para que siga cayendo bajo el
-- cascada de borrado de la solicitud.

ALTER TABLE comentarios ADD COLUMN tarea_id bigint;

ALTER TABLE comentarios
    ADD CONSTRAINT fk_comentarios_tarea FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE;

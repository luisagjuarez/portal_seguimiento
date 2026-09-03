-- Fase 1.21 — Adjuntos en tareas (mismo patrón N:M ya usado para solicitudes_adjuntos,
-- sin ON DELETE CASCADE por la misma razón: delete_tarea es borrado lógico, nunca DELETE FROM).

CREATE TABLE tareas_adjuntos (
    tarea_id bigint NOT NULL REFERENCES tareas(id),
    adjunto_id bigint NOT NULL REFERENCES adjuntos(id),
    PRIMARY KEY (tarea_id, adjunto_id)
);

CREATE INDEX idx_tareas_adjuntos_adjunto ON tareas_adjuntos (adjunto_id);

-- Fase 1.18 — Fecha de entrega + responsable de atención de la solicitud
--
-- solicitudes.solicitante es quien PIDIÓ la solicitud; no existía quién es responsable de
-- ATENDERLA, ni una fecha de entrega comprometida (solo fecha_completado, que es cuándo se
-- cerró). Se agregan ambas columnas, obligatorias en la API (no a nivel BD, mismo criterio que
-- fecha_completado) desde que el estatus llega a "Planeado".

ALTER TABLE solicitudes ADD COLUMN fecha_entrega date;
ALTER TABLE solicitudes ADD COLUMN responsable_atencion_id bigint REFERENCES miembros_equipo(id);

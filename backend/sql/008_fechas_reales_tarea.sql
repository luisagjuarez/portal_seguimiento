-- Fase 2 extra: fecha_inicio/fecha_fin de tareas son las fechas PLANEADAS. Se agregan
-- fecha_inicio_real/fecha_fin_real para registrar cuándo se comenzó y terminó de verdad,
-- y poder comparar planeado vs. real. Nullable: una tarea puede no haber arrancado o no
-- haber terminado todavía.

ALTER TABLE tareas ADD COLUMN fecha_inicio_real date;
ALTER TABLE tareas ADD COLUMN fecha_fin_real date;

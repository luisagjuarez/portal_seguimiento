-- Fase 1.17 — Semáforo de prioridad (1-5)
--
-- solicitudes.orden_prioridad era varchar(100) de texto libre, sin validación de valores.
-- Se convierte a un entero validado 1-5 según 00_ARCHIVOS/matriz_prioridades_scrum.md
-- (1=Crítica .. 5=Trivial), con default 3 (Media) por la regla de negocio #1 de esa matriz.
-- Los valores reales existentes hoy son '1','2','3','5', vacíos y NULL (nada fuera de 1-5),
-- migración segura.

ALTER TABLE solicitudes ALTER COLUMN orden_prioridad TYPE integer
  USING NULLIF(orden_prioridad, '')::integer;

UPDATE solicitudes SET orden_prioridad = 3
  WHERE orden_prioridad IS NULL OR orden_prioridad NOT BETWEEN 1 AND 5;

ALTER TABLE solicitudes ALTER COLUMN orden_prioridad SET DEFAULT 3;
ALTER TABLE solicitudes ALTER COLUMN orden_prioridad SET NOT NULL;
ALTER TABLE solicitudes ADD CONSTRAINT chk_orden_prioridad CHECK (orden_prioridad BETWEEN 1 AND 5);

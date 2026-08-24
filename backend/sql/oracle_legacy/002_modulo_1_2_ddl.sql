-- ============================================================================
-- Fase 1.2 — Interfaz Chat Web
-- ============================================================================
-- Este script se ejecuta UNA VEZ contra la base de datos REAL de DOVELA, después de
-- 001_modulo_1_1_ddl.sql. Agrega una sola columna: sin ella no habría forma de saber
-- por qué canal (correo, chat, ERP, API, archivo) entró cada solicitud en las fases
-- siguientes del roadmap.
--
-- DEFAULT 'EMAIL' cubre retroactivamente las filas que ya existan (todas las creadas
-- hasta ahora vinieron del worker de correo del Módulo 1.1).
-- ============================================================================

ALTER TABLE EBA_DEMO_MD_PROJECTS ADD (CANAL_ORIGEN VARCHAR2(30) DEFAULT 'EMAIL' NOT NULL);

-- Autenticación real (usuario/contraseña), roles Scrum sobre miembros_equipo, y borrado
-- lógico (soft-delete) de solicitudes/tareas/comentarios/hitos para poder atribuir
-- creación/edición/borrado a una persona real.

CREATE TABLE roles_scrum (
    codigo               varchar(20) NOT NULL,
    descripcion          varchar(255) NOT NULL,
    orden_visualizacion  integer NOT NULL,
    creado_en            timestamptz NOT NULL DEFAULT now(),
    creado_por           varchar(255) NOT NULL DEFAULT current_user,
    actualizado_en       timestamptz NOT NULL DEFAULT now(),
    actualizado_por      varchar(255) NOT NULL DEFAULT current_user,
    CONSTRAINT roles_scrum_pk PRIMARY KEY (codigo)
);

INSERT INTO roles_scrum (codigo, descripcion, orden_visualizacion) VALUES
    ('PRODUCT OWNER', 'Product Owner', 1),
    ('SCRUM MASTER',  'Scrum Master',  2),
    ('TEAM',          'Team',          3);

ALTER TABLE miembros_equipo
    ADD COLUMN password_hash   varchar(255),
    ADD COLUMN codigo_rol_scrum varchar(20),
    ADD COLUMN acceso_activo   boolean NOT NULL DEFAULT false;

ALTER TABLE miembros_equipo
    ADD CONSTRAINT fk_miembros_equipo_rol_scrum
    FOREIGN KEY (codigo_rol_scrum) REFERENCES roles_scrum(codigo);

UPDATE miembros_equipo SET codigo_rol_scrum = CASE
    WHEN usuario IN ('DOVELA_JC', 'DOVELA_AR') THEN 'PRODUCT OWNER'
    WHEN usuario = 'DOVELA_LG' THEN 'SCRUM MASTER'
    ELSE 'TEAM'
END;

ALTER TABLE solicitudes ADD COLUMN borrado_en timestamptz, ADD COLUMN borrado_por varchar(255);
ALTER TABLE tareas      ADD COLUMN borrado_en timestamptz, ADD COLUMN borrado_por varchar(255);
ALTER TABLE comentarios ADD COLUMN borrado_en timestamptz, ADD COLUMN borrado_por varchar(255);
ALTER TABLE hitos       ADD COLUMN borrado_en timestamptz, ADD COLUMN borrado_por varchar(255);

-- Solicitudes recurrentes: catálogo de plantillas cruzado con tipos_solicitud (no lo
-- reemplaza). Cada plantilla define un listado ordenado de tareas (responsable fijo, fechas
-- como offset de días desde la fecha de creación de la solicitud) que se generan en lote al
-- crear una solicitud de ese tipo eligiendo la plantilla.

CREATE TABLE plantillas_solicitud (
    id                       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre                   varchar(255) NOT NULL,
    tipo_solicitud_id        bigint NOT NULL REFERENCES tipos_solicitud(id),
    descripcion_default      text,
    orden_prioridad_default  integer NOT NULL DEFAULT 3
        CHECK (orden_prioridad_default BETWEEN 1 AND 5),
    creado_en                timestamptz NOT NULL DEFAULT now(),
    creado_por               varchar(255) NOT NULL,
    actualizado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_por          varchar(255) NOT NULL,
    borrado_en               timestamptz,
    borrado_por              varchar(255)
);

CREATE TABLE plantilla_solicitud_tareas (
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plantilla_solicitud_id  bigint NOT NULL REFERENCES plantillas_solicitud(id) ON DELETE CASCADE,
    orden                   integer NOT NULL,
    nombre                  varchar(255) NOT NULL,
    descripcion             text,
    responsable_id          bigint REFERENCES miembros_equipo(id),
    offset_inicio_dias      integer NOT NULL DEFAULT 0 CHECK (offset_inicio_dias >= 0),
    offset_fin_dias         integer NOT NULL DEFAULT 0 CHECK (offset_fin_dias >= offset_inicio_dias),
    horas_estimadas         integer
);

CREATE INDEX idx_plantilla_solicitud_tareas_plantilla ON plantilla_solicitud_tareas(plantilla_solicitud_id);

-- Trazabilidad: de qué plantilla vino cada solicitud generada (nullable: la mayoría de las
-- solicitudes no vienen de una plantilla).
ALTER TABLE solicitudes ADD COLUMN plantilla_solicitud_id bigint REFERENCES plantillas_solicitud(id);
CREATE INDEX idx_solicitudes_plantilla_solicitud_id ON solicitudes(plantilla_solicitud_id);

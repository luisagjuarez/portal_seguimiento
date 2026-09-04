-- Punto 5 (2026-09-04): número de Service Request del EBS de Oracle a nivel solicitud.
-- Texto libre, nunca obligatorio (el equipo interno lo llena vía formulario; el chat/correo y
-- el rol Externo no lo piden).

ALTER TABLE solicitudes ADD COLUMN sr_ebs varchar(100);

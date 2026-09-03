import { PRIORIDAD_INFO } from "../constants/prioridad.js";

// Una solicitud Completada ya no está "en riesgo" por su prioridad — se apaga el color a gris
// claro (independiente del semáforo de vencimiento, que ya se apaga por separado).
export default function PrioridadBadge({ nivel, codigoEstatus }) {
  const info = PRIORIDAD_INFO[nivel];
  if (!info) {
    return null;
  }
  const clase = codigoEstatus === "COMPLETADO" ? "prioridad-completada" : info.clase;
  return <span className={`prioridad-badge ${clase}`}>{info.etiqueta}</span>;
}

import { PRIORIDAD_INFO } from "../constants/prioridad.js";

export default function PrioridadBadge({ nivel }) {
  const info = PRIORIDAD_INFO[nivel];
  if (!info) {
    return null;
  }
  return <span className={`prioridad-badge ${info.clase}`}>{info.etiqueta}</span>;
}

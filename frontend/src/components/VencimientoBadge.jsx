import { claseVencimiento } from "../utils/vencimiento.js";

export default function VencimientoBadge({ fechaEntrega, codigoEstatus }) {
  const info = claseVencimiento(fechaEntrega, codigoEstatus);
  if (!info) {
    return null;
  }
  return (
    <span className={`vencimiento-badge ${info.clase}`}>
      {info.etiqueta} ({fechaEntrega})
    </span>
  );
}

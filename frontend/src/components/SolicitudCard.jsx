import PrioridadBadge from "./PrioridadBadge.jsx";
import VencimientoBadge from "./VencimientoBadge.jsx";

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function SolicitudCard({ solicitud, onSeleccionar }) {
  return (
    <div
      className="solicitud-card solicitud-card-clicable"
      role="button"
      tabIndex={0}
      onClick={() => onSeleccionar(solicitud.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSeleccionar(solicitud.id);
        }
      }}
    >
      <h3>{solicitud.nombre}</h3>
      <p>
        <strong>Cliente:</strong> {solicitud.cliente || "Sin definir"}
      </p>
      <p>
        <strong>Tipo:</strong> {solicitud.tipo || "Sin definir"}
      </p>
      <p>
        <strong>Solicitante:</strong> {solicitud.solicitante || "Sin identificar"}
      </p>
      <p>
        <strong>Prioridad:</strong> <PrioridadBadge nivel={solicitud.orden_prioridad} />
      </p>
      {solicitud.fecha_entrega && (
        <p>
          <VencimientoBadge fechaEntrega={solicitud.fecha_entrega} codigoEstatus={solicitud.codigo_estatus} />
        </p>
      )}
      <p>
        <span className="solicitud-estatus">{solicitud.estatus_descripcion || solicitud.codigo_estatus}</span>
      </p>
      <p className="solicitud-fecha">{formatearFecha(solicitud.creado_en)}</p>
    </div>
  );
}

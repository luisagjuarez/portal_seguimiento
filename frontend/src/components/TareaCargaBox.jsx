import { useNavigate } from "react-router-dom";
import PrioridadBadge from "./PrioridadBadge.jsx";

export default function TareaCargaBox({ tarea }) {
  const navigate = useNavigate();

  return (
    <div
      className="solicitud-card solicitud-card-clicable tarea-carga-box"
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/tareas/${tarea.id}`)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          navigate(`/tareas/${tarea.id}`);
        }
      }}
    >
      <h3>{tarea.nombre}</h3>
      <p>
        <strong>Solicitud:</strong> {tarea.solicitud_nombre}
      </p>
      <p>
        <strong>Cliente:</strong> {tarea.cliente || "Sin definir"}
      </p>
      <p>
        <strong>Inicio:</strong> {tarea.fecha_inicio} · <strong>Fin:</strong> {tarea.fecha_fin}
      </p>
      <p>
        <strong>Horas programadas:</strong> {tarea.horas_estimadas ?? "Sin definir"}
      </p>
      <p>
        <PrioridadBadge nivel={tarea.solicitud_prioridad} codigoEstatus={tarea.solicitud_codigo_estatus} />
      </p>
    </div>
  );
}

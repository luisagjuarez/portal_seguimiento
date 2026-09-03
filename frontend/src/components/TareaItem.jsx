import { CLASE_POR_ESTATUS } from "../constants/estatusTarea.js";
import PrioridadBadge from "./PrioridadBadge.jsx";
import VencimientoBadge from "./VencimientoBadge.jsx";

export default function TareaItem({ tarea, onEditar, onBorrar, onAbrirDetalle }) {
  const claseEstatus = CLASE_POR_ESTATUS[tarea.codigo_estatus_tarea] || "";

  return (
    <div
      className="tarea-item tarea-item-clicable"
      role="button"
      tabIndex={0}
      onClick={() => onAbrirDetalle(tarea.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onAbrirDetalle(tarea.id);
        }
      }}
    >
      <div className="tarea-item-info">
        <h4>{tarea.nombre}</h4>
        {tarea.descripcion && <p>{tarea.descripcion}</p>}
        <p className="tarea-item-meta">
          <span>Responsable: {tarea.responsable || "Sin asignar"}</span>
          <PrioridadBadge nivel={tarea.solicitud_prioridad} codigoEstatus={tarea.solicitud_codigo_estatus} />
          <VencimientoBadge
            fechaEntrega={tarea.solicitud_fecha_entrega}
            codigoEstatus={tarea.codigo_estatus_tarea}
          />
          <span className={`tarea-estado ${claseEstatus}`}>
            {tarea.estatus_tarea_descripcion || tarea.codigo_estatus_tarea}
          </span>
        </p>
      </div>
      <div className="tarea-item-acciones">
        <button
          type="button"
          className="secundario"
          onClick={(event) => {
            event.stopPropagation();
            onEditar(tarea);
          }}
        >
          Actualizar
        </button>
        {onBorrar && (
          <button
            type="button"
            className="peligro"
            onClick={(event) => {
              event.stopPropagation();
              onBorrar(tarea);
            }}
          >
            Borrar
          </button>
        )}
      </div>
    </div>
  );
}

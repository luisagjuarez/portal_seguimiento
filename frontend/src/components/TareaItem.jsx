export default function TareaItem({ tarea, onEditar, onBorrar }) {
  const completa = tarea.esta_completa === "Y";

  return (
    <div className="tarea-item">
      <div className="tarea-item-info">
        <h4>{tarea.nombre}</h4>
        {tarea.descripcion && <p>{tarea.descripcion}</p>}
        <p className="tarea-item-meta">
          <span>Responsable: {tarea.responsable || "Sin asignar"}</span>
          <span className={completa ? "tarea-estado tarea-estado-completa" : "tarea-estado"}>
            {completa ? "Completado" : "Pendiente"}
          </span>
        </p>
      </div>
      <div className="tarea-item-acciones">
        <button type="button" className="secundario" onClick={() => onEditar(tarea)}>
          Editar
        </button>
        <button type="button" className="peligro" onClick={() => onBorrar(tarea)}>
          Borrar
        </button>
      </div>
    </div>
  );
}

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function PorHacerItem({ item, onToggle, onEditar, onBorrar, puedeGestionar }) {
  return (
    <div className="comentario-item">
      <label className="por-hacer-item-titulo">
        <input
          type="checkbox"
          checked={item.esta_completa}
          disabled={!puedeGestionar}
          onChange={() => onToggle(item)}
        />
        <span className={item.esta_completa ? "por-hacer-item-completo" : ""}>{item.nombre}</span>
      </label>
      {item.descripcion && <p className="comentario-item-texto">{item.descripcion}</p>}
      <p className="solicitud-fecha">Responsable: {item.responsable || "Sin asignar"}</p>
      <div className="comentario-item-pie">
        <span className="solicitud-fecha">
          {item.creado_por_nombre} · {formatearFecha(item.creado_en)}
          {item.actualizado_en !== item.creado_en && " (editado)"}
        </span>
        {(onEditar || onBorrar) && (
          <div className="comentario-item-acciones">
            {onEditar && (
              <button type="button" className="secundario" onClick={() => onEditar(item)}>
                Editar
              </button>
            )}
            {onBorrar && (
              <button type="button" className="peligro" onClick={() => onBorrar(item)}>
                Borrar
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

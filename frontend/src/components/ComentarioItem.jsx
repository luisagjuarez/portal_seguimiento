function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function ComentarioItem({ comentario, onEditar, onBorrar, mostrarTarea }) {
  return (
    <div className="comentario-item">
      <p className="comentario-item-texto">{comentario.texto_comentario}</p>
      {mostrarTarea && comentario.tarea_nombre && (
        <p className="solicitud-fecha">Tarea: {comentario.tarea_nombre}</p>
      )}
      <div className="comentario-item-pie">
        <span className="solicitud-fecha">
          {comentario.creado_por_nombre} · {formatearFecha(comentario.creado_en)}
          {comentario.actualizado_en !== comentario.creado_en && " (editado)"}
        </span>
        {(onEditar || onBorrar) && (
          <div className="comentario-item-acciones">
            {onEditar && (
              <button type="button" className="secundario" onClick={() => onEditar(comentario)}>
                Editar
              </button>
            )}
            {onBorrar && (
              <button type="button" className="peligro" onClick={() => onBorrar(comentario)}>
                Borrar
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function ComentarioItem({ comentario, onEditar, onBorrar }) {
  return (
    <div className="comentario-item">
      <p className="comentario-item-texto">{comentario.texto_comentario}</p>
      <div className="comentario-item-pie">
        <span className="solicitud-fecha">
          {formatearFecha(comentario.creado_en)}
          {comentario.actualizado_en !== comentario.creado_en && " (editado)"}
        </span>
        <div className="comentario-item-acciones">
          <button type="button" className="secundario" onClick={() => onEditar(comentario)}>
            Editar
          </button>
          <button type="button" className="peligro" onClick={() => onBorrar(comentario)}>
            Borrar
          </button>
        </div>
      </div>
    </div>
  );
}

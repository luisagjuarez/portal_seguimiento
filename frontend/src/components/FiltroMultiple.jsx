export default function FiltroMultiple({ etiqueta, opciones, valor, onCambiar }) {
  const seleccionados = new Set(valor);

  const alternar = (id) => {
    const idStr = String(id);
    onCambiar(seleccionados.has(idStr) ? valor.filter((v) => v !== idStr) : [...valor, idStr]);
  };

  return (
    <div className="filtro-multiple-wrap">
      <div className="filtro-multiple-encabezado">
        <span>{etiqueta}</span>
        {valor.length > 0 && (
          <button type="button" className="enlace" onClick={() => onCambiar([])}>
            Limpiar
          </button>
        )}
      </div>
      <div className="filtro-multiple-lista">
        {opciones.length === 0 ? (
          <p className="filtro-multiple-vacio">Sin opciones.</p>
        ) : (
          opciones.map((opcion) => (
            <label className="filtro-multiple-item" key={opcion.id}>
              <input
                type="checkbox"
                checked={seleccionados.has(String(opcion.id))}
                onChange={() => alternar(opcion.id)}
              />
              {opcion.etiqueta}
            </label>
          ))
        )}
      </div>
    </div>
  );
}

import { useState } from "react";

export default function FiltroMultiple({ etiqueta, etiquetaTodos, opciones, valor, onCambiar }) {
  const [abierto, setAbierto] = useState(false);
  const seleccionados = new Set(valor);

  const textoBoton =
    valor.length === 0
      ? etiquetaTodos
      : valor.length === 1
        ? opciones.find((o) => String(o.id) === valor[0])?.etiqueta || "1 seleccionado"
        : `${valor.length} seleccionados`;

  const alternar = (id) => {
    const idStr = String(id);
    onCambiar(seleccionados.has(idStr) ? valor.filter((v) => v !== idStr) : [...valor, idStr]);
  };

  return (
    <div className="filtro-multiple-wrap">
      <button
        type="button"
        className="secundario filtro-multiple-boton"
        onClick={() => setAbierto((actual) => !actual)}
      >
        {textoBoton} ▾
      </button>

      {abierto && (
        <div className="filtro-multiple-panel">
          <div className="filtro-multiple-panel-encabezado">
            <strong>{etiqueta}</strong>
            {valor.length > 0 && (
              <button type="button" className="enlace" onClick={() => onCambiar([])}>
                Limpiar
              </button>
            )}
          </div>
          {opciones.length === 0 ? (
            <p>Sin opciones disponibles.</p>
          ) : (
            <div className="filtro-multiple-lista">
              {opciones.map((opcion) => (
                <label className="filtro-multiple-item" key={opcion.id}>
                  <input
                    type="checkbox"
                    checked={seleccionados.has(String(opcion.id))}
                    onChange={() => alternar(opcion.id)}
                  />
                  {opcion.etiqueta}
                </label>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";

function agruparPorArea(miembros) {
  const grupos = new Map();
  for (const miembro of miembros) {
    const area = miembro.perfil || "Sin área";
    if (!grupos.has(area)) grupos.set(area, []);
    grupos.get(area).push(miembro);
  }
  return [...grupos.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

function CheckboxArea({ checked, indeterminado, onChange }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminado;
  }, [indeterminado]);
  return <input type="checkbox" ref={ref} checked={checked} onChange={onChange} />;
}

export default function FiltroResponsableMultiple({ miembros, valor, onCambiar }) {
  const [abierto, setAbierto] = useState(false);
  const seleccionados = new Set(valor);
  const gruposPorArea = agruparPorArea(miembros);

  const etiqueta =
    valor.length === 0
      ? "Todos los responsables"
      : valor.length === 1
        ? miembros.find((m) => String(m.id) === valor[0])?.nombre_completo || "1 responsable"
        : `${valor.length} responsables`;

  const alternarMiembro = (id) => {
    const idStr = String(id);
    onCambiar(seleccionados.has(idStr) ? valor.filter((v) => v !== idStr) : [...valor, idStr]);
  };

  const alternarArea = (miembrosArea) => {
    const idsArea = miembrosArea.map((m) => String(m.id));
    const todosSeleccionados = idsArea.every((id) => seleccionados.has(id));
    if (todosSeleccionados) {
      onCambiar(valor.filter((v) => !idsArea.includes(v)));
    } else {
      onCambiar([...new Set([...valor, ...idsArea])]);
    }
  };

  return (
    <div className="filtro-responsable-wrap">
      <button
        type="button"
        className="secundario filtro-responsable-boton"
        onClick={() => setAbierto((actual) => !actual)}
      >
        {etiqueta} ▾
      </button>

      {abierto && (
        <div className="filtro-responsable-panel">
          <div className="filtro-responsable-panel-encabezado">
            <strong>Responsable de la tarea</strong>
            {valor.length > 0 && (
              <button type="button" className="enlace" onClick={() => onCambiar([])}>
                Limpiar
              </button>
            )}
          </div>
          {gruposPorArea.map(([area, miembrosArea]) => {
            const idsArea = miembrosArea.map((m) => String(m.id));
            const cantidadSeleccionada = idsArea.filter((id) => seleccionados.has(id)).length;
            return (
              <div className="filtro-responsable-grupo" key={area}>
                <label className="filtro-responsable-area">
                  <CheckboxArea
                    checked={cantidadSeleccionada === idsArea.length}
                    indeterminado={cantidadSeleccionada > 0 && cantidadSeleccionada < idsArea.length}
                    onChange={() => alternarArea(miembrosArea)}
                  />
                  {area}
                </label>
                <div className="filtro-responsable-miembros">
                  {miembrosArea.map((miembro) => (
                    <label className="filtro-responsable-miembro" key={miembro.id}>
                      <input
                        type="checkbox"
                        checked={seleccionados.has(String(miembro.id))}
                        onChange={() => alternarMiembro(miembro.id)}
                      />
                      {miembro.nombre_completo}
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

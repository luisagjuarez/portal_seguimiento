let siguienteClaveLocal = 1;

function nuevaTareaVacia() {
  return {
    _clave: siguienteClaveLocal++,
    nombre: "",
    descripcion: "",
    responsableId: "",
    offsetInicioDias: 0,
    offsetFinDias: 0,
    horasEstimadas: "",
  };
}

export default function PlantillaTareasInput({ tareas, onChange, miembros }) {
  const agregarTarea = () => {
    onChange([...tareas, nuevaTareaVacia()]);
  };

  const quitarTarea = (index) => {
    onChange(tareas.filter((_, i) => i !== index));
  };

  const moverTarea = (index, direccion) => {
    const destino = index + direccion;
    if (destino < 0 || destino >= tareas.length) return;
    const copia = [...tareas];
    [copia[index], copia[destino]] = [copia[destino], copia[index]];
    onChange(copia);
  };

  const actualizarCampo = (index, campo, valor) => {
    const copia = [...tareas];
    copia[index] = { ...copia[index], [campo]: valor };
    onChange(copia);
  };

  return (
    <div className="plantilla-tareas-input">
      {tareas.length === 0 && <p className="crear-solicitud-etiqueta">Sin tareas todavía — agrega al menos una.</p>}
      {tareas.map((tarea, index) => (
        <div className="plantilla-tarea-fila" key={tarea._clave ?? index}>
          <div className="plantilla-tarea-fila-encabezado">
            <strong>Tarea {index + 1}</strong>
            <div>
              <button type="button" className="secundario" disabled={index === 0} onClick={() => moverTarea(index, -1)}>
                Subir
              </button>
              <button
                type="button"
                className="secundario"
                disabled={index === tareas.length - 1}
                onClick={() => moverTarea(index, 1)}
              >
                Bajar
              </button>
              <button type="button" className="peligro" onClick={() => quitarTarea(index)}>
                Quitar
              </button>
            </div>
          </div>

          <label>
            Nombre
            <input
              type="text"
              value={tarea.nombre}
              maxLength={255}
              onChange={(event) => actualizarCampo(index, "nombre", event.target.value)}
              required
            />
          </label>

          <label>
            Descripción (opcional)
            <textarea
              rows={2}
              value={tarea.descripcion}
              onChange={(event) => actualizarCampo(index, "descripcion", event.target.value)}
            />
          </label>

          <div className="tarea-form-fila">
            <label>
              Responsable
              <select
                value={tarea.responsableId}
                onChange={(event) => actualizarCampo(index, "responsableId", event.target.value)}
              >
                <option value="">Sin asignar</option>
                {miembros.map((miembro) => (
                  <option key={miembro.id} value={miembro.id}>
                    {miembro.nombre_completo}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Horas estimadas (opcional)
              <input
                type="number"
                min={0}
                value={tarea.horasEstimadas}
                onChange={(event) => actualizarCampo(index, "horasEstimadas", event.target.value)}
              />
            </label>
          </div>

          <div className="tarea-form-fila">
            <label>
              Día de inicio (offset desde la creación)
              <input
                type="number"
                min={0}
                value={tarea.offsetInicioDias}
                onChange={(event) => actualizarCampo(index, "offsetInicioDias", Number(event.target.value))}
                required
              />
            </label>

            <label>
              Día de fin (offset desde la creación)
              <input
                type="number"
                min={0}
                value={tarea.offsetFinDias}
                onChange={(event) => actualizarCampo(index, "offsetFinDias", Number(event.target.value))}
                required
              />
            </label>
          </div>
        </div>
      ))}

      <button type="button" className="secundario" onClick={agregarTarea}>
        Agregar tarea
      </button>
    </div>
  );
}

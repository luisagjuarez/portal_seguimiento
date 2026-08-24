import { useEffect, useState } from "react";
import { crearTarea, actualizarTarea, fetchEstatusTarea, fetchMiembrosEquipo } from "../api.js";

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function TareaFormulario({ solicitudId, tareaInicial, onGuardada, onCancelar }) {
  const [miembros, setMiembros] = useState([]);
  const [estatusTarea, setEstatusTarea] = useState([]);
  const [nombre, setNombre] = useState(tareaInicial?.nombre || "");
  const [descripcion, setDescripcion] = useState(tareaInicial?.descripcion || "");
  const [responsableId, setResponsableId] = useState(tareaInicial?.responsable_id ?? "");
  const [codigoEstatusTarea, setCodigoEstatusTarea] = useState(
    tareaInicial?.codigo_estatus_tarea || "POR HACER",
  );
  const [fechaInicio, setFechaInicio] = useState(tareaInicial?.fecha_inicio || "");
  const [fechaFin, setFechaFin] = useState(tareaInicial?.fecha_fin || "");
  const [horasEstimadas, setHorasEstimadas] = useState(tareaInicial?.horas_estimadas ?? "");
  const [horasReales, setHorasReales] = useState(tareaInicial?.horas_reales ?? "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const esEdicion = Boolean(tareaInicial);

  useEffect(() => {
    fetchMiembrosEquipo()
      .then(setMiembros)
      .catch(() => setError("No se pudo cargar la lista de miembros del equipo."));
    fetchEstatusTarea()
      .then(setEstatusTarea)
      .catch(() => setError("No se pudo cargar el catálogo de estatus de tarea."));
  }, []);

  const enviar = async (event) => {
    event.preventDefault();
    if (!nombre.trim()) {
      setError("El título de la tarea es obligatorio.");
      return;
    }

    setEnviando(true);
    setError(null);
    const datos = {
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      responsableId: responsableId ? Number(responsableId) : null,
      codigoEstatusTarea,
      fechaInicio: fechaInicio || null,
      fechaFin: fechaFin || null,
      horasEstimadas: horasEstimadas !== "" ? Number(horasEstimadas) : null,
      horasReales: horasReales !== "" ? Number(horasReales) : null,
    };
    try {
      const tarea = esEdicion ? await actualizarTarea(tareaInicial.id, datos) : await crearTarea(solicitudId, datos);
      onGuardada(tarea);
    } catch (err) {
      setError(err.message || "No se pudo guardar la tarea. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Título
        <input type="text" value={nombre} maxLength={255} onChange={(event) => setNombre(event.target.value)} required />
      </label>

      <label>
        Descripción
        <textarea rows={3} value={descripcion} onChange={(event) => setDescripcion(event.target.value)} />
      </label>

      <label>
        Responsable
        <select value={responsableId} onChange={(event) => setResponsableId(event.target.value)}>
          <option value="">Sin asignar</option>
          {miembros.map((miembro) => (
            <option key={miembro.id} value={miembro.id}>
              {miembro.nombre_completo}
            </option>
          ))}
        </select>
      </label>

      <label>
        Estado
        <select value={codigoEstatusTarea} onChange={(event) => setCodigoEstatusTarea(event.target.value)}>
          {estatusTarea.map((estatus) => (
            <option key={estatus.codigo} value={estatus.codigo}>
              {estatus.descripcion}
            </option>
          ))}
        </select>
      </label>

      <div className="tarea-form-fila">
        <label>
          Fecha de inicio (opcional)
          <input type="date" value={fechaInicio} onChange={(event) => setFechaInicio(event.target.value)} />
        </label>

        <label>
          Fecha de fin (opcional)
          <input type="date" value={fechaFin} onChange={(event) => setFechaFin(event.target.value)} />
        </label>
      </div>
      {!esEdicion && (
        <p className="adjuntos-ayuda">
          Si se dejan vacías, la tarea inicia hoy y vence en 7 días.
        </p>
      )}

      <div className="tarea-form-fila">
        <label>
          Horas estimadas (opcional)
          <input
            type="number"
            min="0"
            value={horasEstimadas}
            onChange={(event) => setHorasEstimadas(event.target.value)}
          />
        </label>

        <label>
          Horas reales (opcional)
          <input
            type="number"
            min="0"
            value={horasReales}
            onChange={(event) => setHorasReales(event.target.value)}
          />
        </label>
      </div>

      {esEdicion && (
        <p className="tarea-fechas-info">
          Creada: {formatearFecha(tareaInicial.creado_en)} · Modificada: {formatearFecha(tareaInicial.actualizado_en)}
        </p>
      )}

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Agregar tarea"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

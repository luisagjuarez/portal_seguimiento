import { useEffect, useState } from "react";
import { crearTarea, actualizarTarea, fetchMiembrosEquipo } from "../api.js";

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function TareaFormulario({ solicitudId, tareaInicial, onGuardada, onCancelar }) {
  const [miembros, setMiembros] = useState([]);
  const [nombre, setNombre] = useState(tareaInicial?.nombre || "");
  const [descripcion, setDescripcion] = useState(tareaInicial?.descripcion || "");
  const [responsableId, setResponsableId] = useState(tareaInicial?.responsable_id ?? "");
  const [estaCompleta, setEstaCompleta] = useState(tareaInicial?.esta_completa || "N");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const esEdicion = Boolean(tareaInicial);

  useEffect(() => {
    fetchMiembrosEquipo()
      .then(setMiembros)
      .catch(() => setError("No se pudo cargar la lista de miembros del equipo."));
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
      estaCompleta,
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
        <select value={estaCompleta} onChange={(event) => setEstaCompleta(event.target.value)}>
          <option value="N">Pendiente</option>
          <option value="Y">Completado</option>
        </select>
      </label>

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

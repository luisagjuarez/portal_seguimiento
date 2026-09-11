import { useEffect, useState } from "react";
import PlantillaTareasInput from "./PlantillaTareasInput.jsx";
import { PRIORIDAD_INFO, NIVELES_PRIORIDAD } from "../constants/prioridad.js";
import { actualizarPlantillaSolicitud, fetchMiembrosEquipo, fetchTiposSolicitud } from "../api.js";

let siguienteClaveLocal = 1;

function tareasDesdeDetalle(tareasDetalle) {
  return tareasDetalle.map((tarea) => ({
    _clave: siguienteClaveLocal++,
    nombre: tarea.nombre,
    descripcion: tarea.descripcion || "",
    responsableId: tarea.responsable_id || "",
    offsetInicioDias: tarea.offset_inicio_dias,
    offsetFinDias: tarea.offset_fin_dias,
    horasEstimadas: tarea.horas_estimadas ?? "",
  }));
}

export default function EditarPlantillaSolicitudFormulario({ plantilla, onGuardado, onCancelar }) {
  const [tipos, setTipos] = useState([]);
  const [miembros, setMiembros] = useState([]);
  const [nombre, setNombre] = useState(plantilla.nombre);
  const [tipoSolicitudId, setTipoSolicitudId] = useState(plantilla.tipo_solicitud_id);
  const [descripcionDefault, setDescripcionDefault] = useState(plantilla.descripcion_default || "");
  const [ordenPrioridadDefault, setOrdenPrioridadDefault] = useState(plantilla.orden_prioridad_default);
  const [tareas, setTareas] = useState(() => tareasDesdeDetalle(plantilla.tareas));
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTiposSolicitud()
      .then(setTipos)
      .catch(() => setError("No se pudo cargar el catálogo de tipos de solicitud."));
    fetchMiembrosEquipo(true)
      .then(setMiembros)
      .catch(() => setError("No se pudo cargar la lista de miembros del equipo."));
  }, []);

  const enviar = async (event) => {
    event.preventDefault();
    if (!nombre.trim() || !tipoSolicitudId) {
      setError("Completa nombre y tipo de solicitud antes de guardar la plantilla.");
      return;
    }
    if (tareas.length === 0) {
      setError("Agrega al menos una tarea a la plantilla.");
      return;
    }
    if (tareas.some((tarea) => !tarea.nombre.trim())) {
      setError("Todas las tareas necesitan un nombre.");
      return;
    }
    if (tareas.some((tarea) => Number(tarea.offsetFinDias) < Number(tarea.offsetInicioDias))) {
      setError("En cada tarea, el día de fin no puede ser menor que el día de inicio.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const actualizada = await actualizarPlantillaSolicitud(plantilla.id, {
        nombre: nombre.trim(),
        tipoSolicitudId: Number(tipoSolicitudId),
        descripcionDefault: descripcionDefault.trim(),
        ordenPrioridadDefault,
        tareas,
      });
      onGuardado(actualizada);
    } catch (err) {
      setError(err.message || "No se pudo guardar la plantilla. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Nombre de la plantilla
        <input type="text" value={nombre} maxLength={255} onChange={(event) => setNombre(event.target.value)} required />
      </label>

      <label>
        Tipo de solicitud
        <select value={tipoSolicitudId} onChange={(event) => setTipoSolicitudId(event.target.value)} required>
          {tipos.map((t) => (
            <option key={t.id} value={t.id}>
              {t.tipo}
            </option>
          ))}
        </select>
      </label>

      <label>
        Descripción por defecto (opcional)
        <textarea rows={3} value={descripcionDefault} onChange={(event) => setDescripcionDefault(event.target.value)} />
      </label>

      <label>
        Prioridad por defecto
        <select value={ordenPrioridadDefault} onChange={(event) => setOrdenPrioridadDefault(Number(event.target.value))}>
          {NIVELES_PRIORIDAD.map((nivel) => (
            <option key={nivel} value={nivel}>
              {nivel} - {PRIORIDAD_INFO[nivel].etiqueta}
            </option>
          ))}
        </select>
      </label>

      <div>
        <p className="crear-solicitud-etiqueta">Tareas de la plantilla</p>
        <PlantillaTareasInput tareas={tareas} onChange={setTareas} miembros={miembros} />
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : "Guardar cambios"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

import { useEffect, useState } from "react";
import { crearPorHacer, actualizarPorHacer, fetchMiembrosEquipo } from "../api.js";

export default function PorHacerFormulario({ tareaId, itemInicial, onGuardado, onCancelar }) {
  const [miembros, setMiembros] = useState([]);
  const [nombre, setNombre] = useState(itemInicial?.nombre || "");
  const [descripcion, setDescripcion] = useState(itemInicial?.descripcion || "");
  const [responsableId, setResponsableId] = useState(itemInicial?.responsable_id ?? "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const esEdicion = Boolean(itemInicial);

  useEffect(() => {
    fetchMiembrosEquipo()
      .then(setMiembros)
      .catch(() => setError("No se pudo cargar la lista de miembros del equipo."));
  }, []);

  const enviar = async (event) => {
    event.preventDefault();
    if (!nombre.trim()) {
      setError("El nombre del ítem no puede estar vacío.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const item = esEdicion
        ? await actualizarPorHacer(itemInicial.id, {
            nombre: nombre.trim(),
            descripcion: descripcion.trim() || null,
            responsableId: responsableId || null,
            estaCompleta: itemInicial.esta_completa,
          })
        : await crearPorHacer(tareaId, {
            nombre: nombre.trim(),
            descripcion: descripcion.trim() || null,
            responsableId: responsableId || null,
          });
      onGuardado(item);
    } catch (err) {
      setError(err.message || "No se pudo guardar el ítem. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Nombre
        <input type="text" value={nombre} onChange={(event) => setNombre(event.target.value)} required />
      </label>

      <label>
        Descripción (opcional)
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

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Agregar ítem"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

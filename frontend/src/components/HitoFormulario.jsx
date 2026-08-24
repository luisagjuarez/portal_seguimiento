import { useState } from "react";
import { crearHitoTarea, actualizarHitoTarea } from "../api.js";

export default function HitoFormulario({ tareaId, hitoInicial, onGuardado, onCancelar }) {
  const [nombre, setNombre] = useState(hitoInicial?.nombre || "");
  const [descripcion, setDescripcion] = useState(hitoInicial?.descripcion || "");
  const [fechaVencimiento, setFechaVencimiento] = useState(hitoInicial?.fecha_vencimiento || "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const esEdicion = Boolean(hitoInicial);

  const enviar = async (event) => {
    event.preventDefault();
    if (!nombre.trim() || !fechaVencimiento) {
      setError("Completa nombre y fecha de vencimiento antes de guardar.");
      return;
    }

    setEnviando(true);
    setError(null);
    const datos = {
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      fechaVencimiento,
    };
    try {
      const hito = esEdicion ? await actualizarHitoTarea(tareaId, datos) : await crearHitoTarea(tareaId, datos);
      onGuardado(hito);
    } catch (err) {
      setError(err.message || "No se pudo guardar el hito. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Nombre
        <input type="text" value={nombre} maxLength={255} onChange={(event) => setNombre(event.target.value)} required />
      </label>

      <label>
        Descripción
        <textarea rows={3} value={descripcion} onChange={(event) => setDescripcion(event.target.value)} />
      </label>

      <label>
        Fecha de vencimiento
        <input
          type="date"
          value={fechaVencimiento}
          onChange={(event) => setFechaVencimiento(event.target.value)}
          required
        />
      </label>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Agregar hito"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

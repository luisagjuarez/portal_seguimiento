import { useState } from "react";
import { crearEnlaceTarea } from "../api.js";

export default function EnlaceTareaFormulario({ tareaId, onGuardado, onCancelar }) {
  const [tipoEnlace, setTipoEnlace] = useState("");
  const [url, setUrl] = useState("");
  const [aplicacionId, setAplicacionId] = useState("");
  const [paginaAplicacion, setPaginaAplicacion] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (event) => {
    event.preventDefault();
    if (!tipoEnlace.trim()) {
      setError("Indica el tipo de enlace antes de guardar.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const enlace = await crearEnlaceTarea(tareaId, {
        tipoEnlace: tipoEnlace.trim(),
        url: url.trim() || null,
        aplicacionId: aplicacionId || null,
        paginaAplicacion: paginaAplicacion || null,
        descripcion: descripcion.trim() || null,
      });
      onGuardado(enlace);
    } catch (err) {
      setError(err.message || "No se pudo guardar el enlace. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Tipo de enlace
        <input
          type="text"
          value={tipoEnlace}
          maxLength={20}
          placeholder="URL, Documento, Aplicación..."
          onChange={(event) => setTipoEnlace(event.target.value)}
          required
        />
      </label>

      <label>
        URL (opcional)
        <input
          type="text"
          value={url}
          maxLength={255}
          placeholder="https://..."
          onChange={(event) => setUrl(event.target.value)}
        />
      </label>

      <div className="tarea-form-fila">
        <label>
          ID de aplicación (opcional)
          <input
            type="number"
            min="1"
            value={aplicacionId}
            onChange={(event) => setAplicacionId(event.target.value)}
          />
        </label>

        <label>
          Página de aplicación (opcional)
          <input
            type="number"
            min="1"
            value={paginaAplicacion}
            onChange={(event) => setPaginaAplicacion(event.target.value)}
          />
        </label>
      </div>

      <label>
        Descripción (opcional)
        <textarea rows={3} value={descripcion} onChange={(event) => setDescripcion(event.target.value)} />
      </label>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : "Agregar enlace"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

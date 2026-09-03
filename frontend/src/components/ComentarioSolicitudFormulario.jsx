import { useState } from "react";
import { crearComentarioSolicitud } from "../api.js";

export default function ComentarioSolicitudFormulario({ solicitudId, onGuardado }) {
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (event) => {
    event.preventDefault();
    if (!texto.trim()) {
      setError("El comentario no puede estar vacío.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const comentario = await crearComentarioSolicitud(solicitudId, texto.trim());
      setTexto("");
      onGuardado(comentario);
    } catch (err) {
      setError(err.message || "No se pudo guardar el comentario. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label className="comentario-formulario-campo">
        Nuevo comentario
        <textarea rows={3} value={texto} onChange={(event) => setTexto(event.target.value)} required />
      </label>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : "Agregar comentario"}
        </button>
      </div>
    </form>
  );
}

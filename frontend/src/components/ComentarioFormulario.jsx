import { useState } from "react";
import { crearComentarioTarea, actualizarComentario } from "../api.js";

export default function ComentarioFormulario({ tareaId, comentarioInicial, onGuardado, onCancelar }) {
  const [texto, setTexto] = useState(comentarioInicial?.texto_comentario || "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const esEdicion = Boolean(comentarioInicial);

  const enviar = async (event) => {
    event.preventDefault();
    if (!texto.trim()) {
      setError("El comentario no puede estar vacío.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const comentario = esEdicion
        ? await actualizarComentario(comentarioInicial.id, texto.trim())
        : await crearComentarioTarea(tareaId, texto.trim());
      onGuardado(comentario);
    } catch (err) {
      setError(err.message || "No se pudo guardar el comentario. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Comentario
        <textarea rows={4} value={texto} onChange={(event) => setTexto(event.target.value)} required />
      </label>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Agregar comentario"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

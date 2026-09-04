import { useEffect, useState } from "react";
import MencionesTextarea from "./MencionesTextarea.jsx";
import { actualizarComentario, crearComentarioTarea, fetchMiembrosEquipo } from "../api.js";

export default function ComentarioFormulario({ tareaId, comentarioInicial, onGuardado, onCancelar }) {
  const [texto, setTexto] = useState(comentarioInicial?.texto_comentario || "");
  const [miembros, setMiembros] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const esEdicion = Boolean(comentarioInicial);

  useEffect(() => {
    // excluir_externos: a nivel tarea nunca se puede arrobar a un Externo (Punto 6, 2026-09-04).
    fetchMiembrosEquipo(true)
      .then(setMiembros)
      .catch(() => {
        /* si falla, el picker simplemente no aparece — escribir @usuario a mano sigue funcionando */
      });
  }, []);

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
      <label className="comentario-formulario-campo">
        Comentario
        <MencionesTextarea texto={texto} setTexto={setTexto} miembros={miembros} />
      </label>
      <p className="comentario-formulario-ayuda">
        Escribe @usuario para mencionar a alguien del equipo, o @todos para notificar a todos.
      </p>

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

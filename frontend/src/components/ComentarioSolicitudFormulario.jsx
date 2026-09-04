import { useEffect, useState } from "react";
import MencionesTextarea from "./MencionesTextarea.jsx";
import { crearComentarioSolicitud, fetchMiembrosEquipo } from "../api.js";

export default function ComentarioSolicitudFormulario({ solicitudId, onGuardado }) {
  const [texto, setTexto] = useState("");
  const [miembros, setMiembros] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // A diferencia de los comentarios de tarea, a nivel solicitud sí se puede arrobar a un
    // Externo (Punto 6, 2026-09-04) — no se excluye del picker.
    fetchMiembrosEquipo()
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
        <MencionesTextarea texto={texto} setTexto={setTexto} miembros={miembros} rows={3} />
      </label>
      <p className="comentario-formulario-ayuda">
        Escribe @usuario para mencionar a alguien, o @todos para notificar a todo el equipo.
      </p>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : "Agregar comentario"}
        </button>
      </div>
    </form>
  );
}

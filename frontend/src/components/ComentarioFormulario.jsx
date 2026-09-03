import { useEffect, useRef, useState } from "react";
import { actualizarComentario, crearComentarioTarea, fetchMiembrosEquipo } from "../api.js";

// Detecta si el cursor está justo después de un "@parcial" sin espacios, para mostrar el
// picker de menciones. Devuelve la posición donde empieza el "@" y el texto ya escrito
// después de él (para filtrar), o null si el cursor no está en una mención.
function detectarMencionEnCurso(texto, posicionCursor) {
  const antesDelCursor = texto.slice(0, posicionCursor);
  const inicioArroba = antesDelCursor.lastIndexOf("@");
  if (inicioArroba === -1) return null;
  const fragmento = antesDelCursor.slice(inicioArroba + 1);
  if (/\s/.test(fragmento)) return null;
  return { inicio: inicioArroba, consulta: fragmento };
}

export default function ComentarioFormulario({ tareaId, comentarioInicial, onGuardado, onCancelar }) {
  const [texto, setTexto] = useState(comentarioInicial?.texto_comentario || "");
  const [miembros, setMiembros] = useState([]);
  const [mencionEnCurso, setMencionEnCurso] = useState(null);
  const [indiceActivo, setIndiceActivo] = useState(0);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const textareaRef = useRef(null);

  const esEdicion = Boolean(comentarioInicial);

  useEffect(() => {
    fetchMiembrosEquipo()
      .then(setMiembros)
      .catch(() => {
        /* si falla, el picker simplemente no aparece — escribir @usuario a mano sigue funcionando */
      });
  }, []);

  const alCambiarTexto = (event) => {
    const nuevoTexto = event.target.value;
    setTexto(nuevoTexto);
    setMencionEnCurso(detectarMencionEnCurso(nuevoTexto, event.target.selectionStart));
    setIndiceActivo(0);
  };

  const elegirMencion = (usuario) => {
    if (!mencionEnCurso) return;
    const antes = texto.slice(0, mencionEnCurso.inicio);
    const despues = texto.slice(mencionEnCurso.inicio + 1 + mencionEnCurso.consulta.length);
    const nuevoTexto = `${antes}@${usuario} ${despues}`;
    setTexto(nuevoTexto);
    setMencionEnCurso(null);
    textareaRef.current?.focus();
  };

  const opcionesMencion = mencionEnCurso
    ? [
        { usuario: "todos", nombre_completo: "Todo el equipo" },
        ...miembros.map((m) => ({ usuario: m.usuario, nombre_completo: m.nombre_completo })),
      ].filter(
        (m) =>
          !mencionEnCurso.consulta ||
          m.usuario.toLowerCase().includes(mencionEnCurso.consulta.toLowerCase()) ||
          m.nombre_completo.toLowerCase().includes(mencionEnCurso.consulta.toLowerCase()),
      )
    : [];

  const alPresionarTecla = (event) => {
    if (!mencionEnCurso || opcionesMencion.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIndiceActivo((indice) => (indice + 1) % opcionesMencion.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setIndiceActivo((indice) => (indice - 1 + opcionesMencion.length) % opcionesMencion.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      elegirMencion(opcionesMencion[indiceActivo].usuario);
    } else if (event.key === "Escape") {
      setMencionEnCurso(null);
    }
  };

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
        <textarea
          ref={textareaRef}
          rows={4}
          value={texto}
          onChange={alCambiarTexto}
          onKeyDown={alPresionarTecla}
          onBlur={() => setTimeout(() => setMencionEnCurso(null), 150)}
          required
        />
        {mencionEnCurso && opcionesMencion.length > 0 && (
          <ul className="mencion-picker">
            {opcionesMencion.map((opcion, indice) => (
              <li key={opcion.usuario}>
                <button
                  type="button"
                  className={indice === indiceActivo ? "mencion-picker-activa" : undefined}
                  onMouseDown={() => elegirMencion(opcion.usuario)}
                  onMouseEnter={() => setIndiceActivo(indice)}
                >
                  @{opcion.usuario} <span className="mencion-picker-nombre">{opcion.nombre_completo}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
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

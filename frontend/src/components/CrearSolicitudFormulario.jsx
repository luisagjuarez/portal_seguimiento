import { useEffect, useState } from "react";
import ClienteAutocomplete from "./ClienteAutocomplete.jsx";
import AdjuntosInput from "./AdjuntosInput.jsx";
import { crearSolicitudFormulario, fetchMiembrosEquipo, fetchTiposSolicitud } from "../api.js";

export default function CrearSolicitudFormulario({ onCreada, onCancelar }) {
  const [miembros, setMiembros] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [solicitanteEmail, setSolicitanteEmail] = useState("");
  const [titulo, setTitulo] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [tipo, setTipo] = useState("");
  const [cliente, setCliente] = useState(null);
  const [adjuntos, setAdjuntos] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMiembrosEquipo()
      .then(setMiembros)
      .catch(() => setError("No se pudo cargar la lista de miembros del equipo."));
    fetchTiposSolicitud()
      .then(setTipos)
      .catch(() => setError("No se pudo cargar el catálogo de tipos de solicitud."));
  }, []);

  const enviar = async (event) => {
    event.preventDefault();
    if (!solicitanteEmail || !titulo.trim() || !descripcion.trim() || !tipo) {
      setError("Completa solicitante, título, descripción y tipo antes de crear la solicitud.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const respuesta = await crearSolicitudFormulario({
        solicitanteEmail,
        titulo: titulo.trim(),
        descripcion: descripcion.trim(),
        tipo,
        cliente,
        adjuntos,
      });
      onCreada(respuesta);
    } catch (err) {
      setError(err.message || "No se pudo crear la solicitud. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Solicitante
        <select value={solicitanteEmail} onChange={(event) => setSolicitanteEmail(event.target.value)} required>
          <option value="" disabled>
            Selecciona un miembro del equipo...
          </option>
          {miembros.map((miembro) => (
            <option key={miembro.id} value={miembro.correo_electronico || ""} disabled={!miembro.correo_electronico}>
              {miembro.nombre_completo}
              {!miembro.correo_electronico ? " (sin correo registrado)" : ""}
            </option>
          ))}
        </select>
      </label>

      <label>
        Título
        <input
          type="text"
          value={titulo}
          maxLength={500}
          onChange={(event) => setTitulo(event.target.value)}
          required
        />
      </label>

      <label>
        Descripción
        <textarea
          rows={4}
          value={descripcion}
          onChange={(event) => setDescripcion(event.target.value)}
          required
        />
      </label>

      <label>
        Tipo
        <select value={tipo} onChange={(event) => setTipo(event.target.value)} required>
          <option value="" disabled>
            Selecciona un tipo...
          </option>
          {tipos.map((t) => (
            <option key={t.id} value={t.tipo}>
              {t.tipo}
            </option>
          ))}
        </select>
      </label>

      <div>
        <p className="crear-solicitud-etiqueta">Cliente (opcional)</p>
        <ClienteAutocomplete onSelect={setCliente} onSkip={() => setCliente(null)} />
        {cliente && <p className="crear-solicitud-cliente-elegido">Cliente elegido: {cliente}</p>}
      </div>

      <div>
        <p className="crear-solicitud-etiqueta">Adjuntos (opcional)</p>
        <AdjuntosInput archivos={adjuntos} onChange={setAdjuntos} />
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Creando..." : "Crear solicitud"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

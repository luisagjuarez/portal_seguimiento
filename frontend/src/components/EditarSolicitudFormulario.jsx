import { useEffect, useState } from "react";
import ClienteAutocomplete from "./ClienteAutocomplete.jsx";
import { actualizarSolicitud, fetchEstatus, fetchTiposSolicitud } from "../api.js";

export default function EditarSolicitudFormulario({ solicitud, onActualizada, onCancelar }) {
  const [tipos, setTipos] = useState([]);
  const [estatusCatalogo, setEstatusCatalogo] = useState([]);
  const [nombre, setNombre] = useState(solicitud.nombre);
  const [descripcion, setDescripcion] = useState(solicitud.descripcion || "");
  const [tipo, setTipo] = useState(solicitud.tipo || "");
  const [codigoEstatus, setCodigoEstatus] = useState(solicitud.codigo_estatus);
  const [cliente, setCliente] = useState(solicitud.cliente || null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTiposSolicitud()
      .then(setTipos)
      .catch(() => setError("No se pudo cargar el catálogo de tipos de solicitud."));
    fetchEstatus()
      .then(setEstatusCatalogo)
      .catch(() => setError("No se pudo cargar el catálogo de estatus."));
  }, []);

  const enviar = async (event) => {
    event.preventDefault();
    if (!nombre.trim() || !descripcion.trim() || !tipo || !codigoEstatus) {
      setError("Completa título, descripción, tipo y estatus antes de guardar.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const actualizada = await actualizarSolicitud(solicitud.id, {
        nombre: nombre.trim(),
        descripcion: descripcion.trim(),
        cliente,
        tipo,
        codigoEstatus,
      });
      onActualizada(actualizada);
    } catch (err) {
      setError(err.message || "No se pudo actualizar la solicitud. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Título
        <input
          type="text"
          value={nombre}
          maxLength={500}
          onChange={(event) => setNombre(event.target.value)}
          required
        />
      </label>

      <label>
        Descripción
        <textarea rows={4} value={descripcion} onChange={(event) => setDescripcion(event.target.value)} required />
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

      <label>
        Estatus
        <select value={codigoEstatus} onChange={(event) => setCodigoEstatus(event.target.value)} required>
          {estatusCatalogo.map((estatus) => (
            <option key={estatus.codigo} value={estatus.codigo}>
              {estatus.descripcion}
            </option>
          ))}
        </select>
      </label>

      <div>
        <p className="crear-solicitud-etiqueta">Cliente (opcional)</p>
        <ClienteAutocomplete onSelect={setCliente} onSkip={() => setCliente(null)} />
        {cliente && <p className="crear-solicitud-cliente-elegido">Cliente elegido: {cliente}</p>}
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

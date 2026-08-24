import { useEffect, useState } from "react";
import SolicitudCard from "./SolicitudCard.jsx";
import CrearSolicitudFormulario from "./CrearSolicitudFormulario.jsx";
import { fetchEstatus, fetchSolicitudes } from "../api.js";

export default function SolicitudesPage({ onVerDetalle }) {
  const [solicitudes, setSolicitudes] = useState([]);
  const [estatusCatalogo, setEstatusCatalogo] = useState([]);
  const [filtroCliente, setFiltroCliente] = useState("");
  const [filtroNombre, setFiltroNombre] = useState("");
  const [filtroEstatus, setFiltroEstatus] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [mensajeExito, setMensajeExito] = useState(null);

  const cargarSolicitudes = () => {
    setCargando(true);
    setError(null);
    fetchSolicitudes({ cliente: filtroCliente, nombre: filtroNombre, estatus: filtroEstatus })
      .then(setSolicitudes)
      .catch((err) => setError(err.message || "No se pudieron cargar las solicitudes."))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    fetchEstatus()
      .then(setEstatusCatalogo)
      .catch(() => {
        /* el filtro de estatus queda solo con "Todos" si esto falla */
      });
  }, []);

  useEffect(() => {
    const timeoutId = setTimeout(cargarSolicitudes, 300);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroCliente, filtroNombre, filtroEstatus]);

  const alCrearSolicitud = (respuesta) => {
    setMostrarFormulario(false);
    setMensajeExito(`Solicitud #${respuesta.id_solicitud} creada: "${respuesta.titulo}".`);
    cargarSolicitudes();
  };

  return (
    <div className="solicitudes-page">
      <div className="solicitudes-encabezado">
        <h2>Solicitudes</h2>
        <button type="button" onClick={() => setMostrarFormulario(true)}>
          Crear solicitud
        </button>
      </div>

      {mensajeExito && <p className="mensaje-exito">{mensajeExito}</p>}

      <div className="solicitudes-filtros">
        <input
          type="text"
          placeholder="Filtrar por cliente..."
          value={filtroCliente}
          onChange={(event) => setFiltroCliente(event.target.value)}
        />
        <input
          type="text"
          placeholder="Filtrar por nombre de la solicitud..."
          value={filtroNombre}
          onChange={(event) => setFiltroNombre(event.target.value)}
        />
        <select value={filtroEstatus} onChange={(event) => setFiltroEstatus(event.target.value)}>
          <option value="">Todos los estatus</option>
          {estatusCatalogo.map((estatus) => (
            <option key={estatus.codigo} value={estatus.codigo}>
              {estatus.descripcion}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="error-text">{error}</p>}
      {cargando && <p>Cargando solicitudes...</p>}
      {!cargando && !error && solicitudes.length === 0 && <p>No se encontraron solicitudes.</p>}

      <div className="solicitudes-grid">
        {solicitudes.map((solicitud) => (
          <SolicitudCard key={solicitud.id} solicitud={solicitud} onSeleccionar={onVerDetalle} />
        ))}
      </div>

      {mostrarFormulario && (
        <div className="modal-overlay" onClick={() => setMostrarFormulario(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>Nueva solicitud</h3>
            <CrearSolicitudFormulario
              onCreada={alCrearSolicitud}
              onCancelar={() => setMostrarFormulario(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

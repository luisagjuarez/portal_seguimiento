import { useEffect, useState } from "react";
import ClienteAutocomplete from "./ClienteAutocomplete.jsx";
import { PRIORIDAD_INFO, NIVELES_PRIORIDAD } from "../constants/prioridad.js";
import {
  actualizarSolicitud,
  fetchCanalesSolicitud,
  fetchEstatus,
  fetchMiembrosEquipo,
  fetchTiposSolicitud,
} from "../api.js";

function fechaHoy() {
  return new Date().toISOString().slice(0, 10);
}

// Mismo criterio que ESTATUS_REQUIERE_FECHA_ENTREGA en backend/app/api/schemas.py: a partir
// de "Planeado", la fecha de entrega y el responsable de atención son obligatorios.
const ESTATUS_REQUIERE_FECHA_ENTREGA = new Set(["PLANEADO", "EN PROGRESO", "COMPLETADO"]);

export default function EditarSolicitudFormulario({ solicitud, onActualizada, onCancelar }) {
  const [tipos, setTipos] = useState([]);
  const [canales, setCanales] = useState([]);
  const [estatusCatalogo, setEstatusCatalogo] = useState([]);
  const [miembros, setMiembros] = useState([]);
  const [nombre, setNombre] = useState(solicitud.nombre);
  const [descripcion, setDescripcion] = useState(solicitud.descripcion || "");
  const [tipo, setTipo] = useState(solicitud.tipo || "");
  const [canal, setCanal] = useState(solicitud.canal || "");
  const [ordenPrioridad, setOrdenPrioridad] = useState(solicitud.orden_prioridad || 3);
  const [codigoEstatus, setCodigoEstatus] = useState(solicitud.codigo_estatus);
  const [fechaCompletado, setFechaCompletado] = useState(solicitud.fecha_completado || "");
  const [fechaEntrega, setFechaEntrega] = useState(solicitud.fecha_entrega || "");
  const [responsableAtencionId, setResponsableAtencionId] = useState(
    solicitud.responsable_atencion_id || "",
  );
  const [cliente, setCliente] = useState(solicitud.cliente || null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTiposSolicitud()
      .then(setTipos)
      .catch(() => setError("No se pudo cargar el catálogo de tipos de solicitud."));
    fetchCanalesSolicitud()
      .then(setCanales)
      .catch(() => setError("No se pudo cargar el catálogo de canales."));
    fetchEstatus()
      .then(setEstatusCatalogo)
      .catch(() => setError("No se pudo cargar el catálogo de estatus."));
    fetchMiembrosEquipo()
      .then(setMiembros)
      .catch(() => setError("No se pudo cargar la lista de miembros del equipo."));
  }, []);

  const alCambiarEstatus = (nuevoEstatus) => {
    setCodigoEstatus(nuevoEstatus);
    if (nuevoEstatus === "COMPLETADO" && !fechaCompletado) {
      setFechaCompletado(fechaHoy());
    }
  };

  const requiereFechaEntrega = ESTATUS_REQUIERE_FECHA_ENTREGA.has(codigoEstatus);

  const enviar = async (event) => {
    event.preventDefault();
    if (!nombre.trim() || !descripcion.trim() || !tipo || !canal || !codigoEstatus) {
      setError("Completa título, descripción, tipo, canal y estatus antes de guardar.");
      return;
    }
    if (codigoEstatus === "COMPLETADO" && !fechaCompletado) {
      setError("Ingresa la fecha en que se completó la solicitud.");
      return;
    }
    if (requiereFechaEntrega && (!fechaEntrega || !responsableAtencionId)) {
      setError("Ingresa la fecha de entrega y el responsable de atención antes de guardar.");
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
        canal,
        codigoEstatus,
        ordenPrioridad,
        fechaCompletado: codigoEstatus === "COMPLETADO" ? fechaCompletado : null,
        fechaEntrega: requiereFechaEntrega ? fechaEntrega : null,
        responsableAtencionId: requiereFechaEntrega ? Number(responsableAtencionId) : null,
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

      <div className="tarea-form-fila">
        <label>
          Canal
          <select value={canal} onChange={(event) => setCanal(event.target.value)} required>
            <option value="" disabled>
              Selecciona un canal...
            </option>
            {canales.map((c) => (
              <option key={c.id} value={c.canal}>
                {c.canal}
              </option>
            ))}
          </select>
        </label>

        <label>
          Prioridad
          <select value={ordenPrioridad} onChange={(event) => setOrdenPrioridad(Number(event.target.value))}>
            {NIVELES_PRIORIDAD.map((nivel) => (
              <option key={nivel} value={nivel}>
                {nivel} - {PRIORIDAD_INFO[nivel].etiqueta}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="tarea-form-fila">
        <label>
          Estatus
          <select value={codigoEstatus} onChange={(event) => alCambiarEstatus(event.target.value)} required>
            {estatusCatalogo.map((estatus) => (
              <option key={estatus.codigo} value={estatus.codigo}>
                {estatus.descripcion}
              </option>
            ))}
          </select>
        </label>

        {codigoEstatus === "COMPLETADO" && (
          <label>
            Fecha Completado
            <input
              type="date"
              value={fechaCompletado}
              onChange={(event) => setFechaCompletado(event.target.value)}
              required
            />
          </label>
        )}
      </div>

      {requiereFechaEntrega && (
        <div className="tarea-form-fila">
          <label>
            Fecha de entrega
            <input
              type="date"
              value={fechaEntrega}
              onChange={(event) => setFechaEntrega(event.target.value)}
              required
            />
          </label>

          <label>
            Responsable de atención
            <select
              value={responsableAtencionId}
              onChange={(event) => setResponsableAtencionId(event.target.value)}
              required
            >
              <option value="" disabled>
                Selecciona un miembro del equipo...
              </option>
              {miembros.map((miembro) => (
                <option key={miembro.id} value={miembro.id}>
                  {miembro.nombre_completo}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

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

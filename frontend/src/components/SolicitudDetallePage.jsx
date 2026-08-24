import { useEffect, useState } from "react";
import ConfirmModal from "./ConfirmModal.jsx";
import EditarSolicitudFormulario from "./EditarSolicitudFormulario.jsx";
import TareaFormulario from "./TareaFormulario.jsx";
import TareaItem from "./TareaItem.jsx";
import { eliminarSolicitud, eliminarTarea, fetchSolicitudDetalle, fetchTareas } from "../api.js";

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function SolicitudDetallePage({ solicitudId, onRegresar, onVerTarea, esScrumMaster }) {
  const [solicitud, setSolicitud] = useState(null);
  const [tareas, setTareas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [mostrarEditar, setMostrarEditar] = useState(false);
  const [mostrarConfirmarBorrarSolicitud, setMostrarConfirmarBorrarSolicitud] = useState(false);
  const [borrandoSolicitud, setBorrandoSolicitud] = useState(false);

  const [tareaEnEdicion, setTareaEnEdicion] = useState(null);
  const [mostrarFormularioTarea, setMostrarFormularioTarea] = useState(false);
  const [tareaABorrar, setTareaABorrar] = useState(null);
  const [borrandoTarea, setBorrandoTarea] = useState(false);

  const cargarDetalle = () => {
    setCargando(true);
    setError(null);
    Promise.all([fetchSolicitudDetalle(solicitudId), fetchTareas(solicitudId)])
      .then(([detalle, listaTareas]) => {
        setSolicitud(detalle);
        setTareas(listaTareas);
      })
      .catch((err) => setError(err.message || "No se pudo cargar el detalle de la solicitud."))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargarDetalle();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [solicitudId]);

  const alActualizarSolicitud = (detalleActualizado) => {
    setSolicitud(detalleActualizado);
    setMostrarEditar(false);
  };

  const confirmarBorrarSolicitud = async () => {
    setBorrandoSolicitud(true);
    try {
      await eliminarSolicitud(solicitudId);
      onRegresar();
    } catch (err) {
      setError(err.message || "No se pudo borrar la solicitud.");
      setMostrarConfirmarBorrarSolicitud(false);
    } finally {
      setBorrandoSolicitud(false);
    }
  };

  const alGuardarTarea = () => {
    setMostrarFormularioTarea(false);
    setTareaEnEdicion(null);
    cargarDetalle();
  };

  const confirmarBorrarTarea = async () => {
    setBorrandoTarea(true);
    try {
      await eliminarTarea(tareaABorrar.id);
      setTareaABorrar(null);
      cargarDetalle();
    } catch (err) {
      setError(err.message || "No se pudo borrar la tarea.");
    } finally {
      setBorrandoTarea(false);
    }
  };

  if (cargando) {
    return <p>Cargando solicitud...</p>;
  }

  if (error && !solicitud) {
    return (
      <div>
        <p className="error-text">{error}</p>
        <button type="button" className="secundario" onClick={onRegresar}>
          ← Regresar
        </button>
      </div>
    );
  }

  return (
    <div className="solicitud-detalle-page">
      <button type="button" className="secundario" onClick={onRegresar}>
        ← Regresar
      </button>

      {error && <p className="error-text">{error}</p>}

      <div className="solicitud-detalle-info">
        <div className="solicitudes-encabezado">
          <h2>{solicitud.nombre}</h2>
          <span className="solicitud-estatus">{solicitud.estatus_descripcion || solicitud.codigo_estatus}</span>
        </div>
        <p>{solicitud.descripcion}</p>
        <p>
          <strong>Cliente:</strong> {solicitud.cliente || "Sin definir"}
        </p>
        <p>
          <strong>Tipo:</strong> {solicitud.tipo || "Sin definir"}
        </p>
        <p>
          <strong>Solicitante:</strong> {solicitud.solicitante || "Sin identificar"}
        </p>
        <p className="solicitud-fecha">Creada: {formatearFecha(solicitud.creado_en)}</p>

        <div className="resumen-acciones">
          <button type="button" onClick={() => setMostrarEditar(true)}>
            Editar Solicitud
          </button>
          <button type="button" className="peligro" onClick={() => setMostrarConfirmarBorrarSolicitud(true)}>
            Borrar Solicitud
          </button>
        </div>
      </div>

      <div className="solicitud-detalle-tareas">
        <div className="solicitudes-encabezado">
          <h3>Tareas</h3>
          {esScrumMaster && (
            <button
              type="button"
              onClick={() => {
                setTareaEnEdicion(null);
                setMostrarFormularioTarea(true);
              }}
            >
              Agregar Tarea
            </button>
          )}
        </div>

        {!esScrumMaster && (
          <p className="adjuntos-ayuda">Solo el Scrum Master puede agregar tareas.</p>
        )}
        {tareas.length === 0 && <p>Esta solicitud todavía no tiene tareas.</p>}

        <div className="tarea-lista">
          {tareas.map((tarea) => (
            <TareaItem
              key={tarea.id}
              tarea={tarea}
              onEditar={(t) => {
                setTareaEnEdicion(t);
                setMostrarFormularioTarea(true);
              }}
              onBorrar={setTareaABorrar}
              onAbrirDetalle={onVerTarea}
            />
          ))}
        </div>
      </div>

      {mostrarEditar && (
        <div className="modal-overlay" onClick={() => setMostrarEditar(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>Editar solicitud</h3>
            <EditarSolicitudFormulario
              solicitud={solicitud}
              onActualizada={alActualizarSolicitud}
              onCancelar={() => setMostrarEditar(false)}
            />
          </div>
        </div>
      )}

      {mostrarConfirmarBorrarSolicitud && (
        <ConfirmModal
          titulo="Borrar solicitud"
          mensaje={`¿Seguro que quieres borrar la solicitud "${solicitud.nombre}"? Esta acción no se puede deshacer.`}
          confirmando={borrandoSolicitud}
          onConfirmar={confirmarBorrarSolicitud}
          onCancelar={() => setMostrarConfirmarBorrarSolicitud(false)}
        />
      )}

      {mostrarFormularioTarea && (
        <div
          className="modal-overlay"
          onClick={() => {
            setMostrarFormularioTarea(false);
            setTareaEnEdicion(null);
          }}
        >
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>{tareaEnEdicion ? "Editar tarea" : "Nueva tarea"}</h3>
            <TareaFormulario
              solicitudId={solicitudId}
              tareaInicial={tareaEnEdicion}
              onGuardada={alGuardarTarea}
              onCancelar={() => {
                setMostrarFormularioTarea(false);
                setTareaEnEdicion(null);
              }}
            />
          </div>
        </div>
      )}

      {tareaABorrar && (
        <ConfirmModal
          titulo="Borrar tarea"
          mensaje={`¿Seguro que quieres borrar la tarea "${tareaABorrar.nombre}"?`}
          confirmando={borrandoTarea}
          onConfirmar={confirmarBorrarTarea}
          onCancelar={() => setTareaABorrar(null)}
        />
      )}
    </div>
  );
}

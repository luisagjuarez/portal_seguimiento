import { useEffect, useState } from "react";
import ConfirmModal from "./ConfirmModal.jsx";
import HitoFormulario from "./HitoFormulario.jsx";
import ComentarioFormulario from "./ComentarioFormulario.jsx";
import ComentarioItem from "./ComentarioItem.jsx";
import EnlaceTareaFormulario from "./EnlaceTareaFormulario.jsx";
import EnlaceTareaItem from "./EnlaceTareaItem.jsx";
import TareaFormulario from "./TareaFormulario.jsx";
import {
  eliminarComentario,
  eliminarHitoTarea,
  fetchComentariosTarea,
  fetchEnlacesTarea,
  fetchHitoDeTarea,
  fetchTareaDetalle,
} from "../api.js";

const CLASE_POR_ESTATUS = {
  "POR HACER": "tarea-estado-por-hacer",
  "EN PROGRESO": "tarea-estado-en-progreso",
  "EN REVISION": "tarea-estado-en-revision",
  COMPLETADO: "tarea-estado-completa",
};

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function TareaDetallePage({ tareaId, onRegresar, onVerSolicitud }) {
  const [tarea, setTarea] = useState(null);
  const [hito, setHito] = useState(null);
  const [comentarios, setComentarios] = useState([]);
  const [enlaces, setEnlaces] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [mostrarFormularioTarea, setMostrarFormularioTarea] = useState(false);

  const [mostrarFormularioHito, setMostrarFormularioHito] = useState(false);
  const [mostrarConfirmarBorrarHito, setMostrarConfirmarBorrarHito] = useState(false);
  const [borrandoHito, setBorrandoHito] = useState(false);

  const [comentarioEnEdicion, setComentarioEnEdicion] = useState(null);
  const [mostrarFormularioComentario, setMostrarFormularioComentario] = useState(false);
  const [comentarioABorrar, setComentarioABorrar] = useState(null);
  const [borrandoComentario, setBorrandoComentario] = useState(false);

  const [mostrarFormularioEnlace, setMostrarFormularioEnlace] = useState(false);

  const [pestanaActiva, setPestanaActiva] = useState("comentarios");

  const cargarDetalle = () => {
    setCargando(true);
    setError(null);
    Promise.all([
      fetchTareaDetalle(tareaId),
      fetchHitoDeTarea(tareaId),
      fetchComentariosTarea(tareaId),
      fetchEnlacesTarea(tareaId),
    ])
      .then(([detalleTarea, hitoActual, listaComentarios, listaEnlaces]) => {
        setTarea(detalleTarea);
        setHito(hitoActual);
        setComentarios(listaComentarios);
        setEnlaces(listaEnlaces);
      })
      .catch((err) => setError(err.message || "No se pudo cargar el detalle de la tarea."))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargarDetalle();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tareaId]);

  const alGuardarTarea = () => {
    setMostrarFormularioTarea(false);
    cargarDetalle();
  };

  const alGuardarHito = (hitoActualizado) => {
    setHito(hitoActualizado);
    setMostrarFormularioHito(false);
  };

  const confirmarBorrarHito = async () => {
    setBorrandoHito(true);
    try {
      await eliminarHitoTarea(tareaId);
      setHito(null);
      setMostrarConfirmarBorrarHito(false);
    } catch (err) {
      setError(err.message || "No se pudo borrar el hito.");
    } finally {
      setBorrandoHito(false);
    }
  };

  const alGuardarComentario = () => {
    setMostrarFormularioComentario(false);
    setComentarioEnEdicion(null);
    cargarDetalle();
  };

  const alGuardarEnlace = () => {
    setMostrarFormularioEnlace(false);
    cargarDetalle();
  };

  const confirmarBorrarComentario = async () => {
    setBorrandoComentario(true);
    try {
      await eliminarComentario(comentarioABorrar.id);
      setComentarioABorrar(null);
      cargarDetalle();
    } catch (err) {
      setError(err.message || "No se pudo borrar el comentario.");
    } finally {
      setBorrandoComentario(false);
    }
  };

  if (cargando) {
    return <p>Cargando tarea...</p>;
  }

  if (error && !tarea) {
    return (
      <div>
        <p className="error-text">{error}</p>
        <button type="button" className="secundario" onClick={onRegresar}>
          ← Regresar
        </button>
      </div>
    );
  }

  const claseEstatus = CLASE_POR_ESTATUS[tarea.codigo_estatus_tarea] || "";

  return (
    <div className="solicitud-detalle-page">
      <button type="button" className="secundario" onClick={onRegresar}>
        ← Regresar
      </button>

      {error && <p className="error-text">{error}</p>}

      <div className="solicitud-detalle-info">
        <div className="solicitudes-encabezado">
          <h2>{tarea.nombre}</h2>
          <span className={`tarea-estado ${claseEstatus}`}>
            {tarea.estatus_tarea_descripcion || tarea.codigo_estatus_tarea}
          </span>
        </div>
        {tarea.descripcion && <p>{tarea.descripcion}</p>}
        <p>
          <strong>Solicitud:</strong>{" "}
          {onVerSolicitud ? (
            <button type="button" className="enlace" onClick={() => onVerSolicitud(tarea.solicitud_id)}>
              {tarea.solicitud_nombre}
            </button>
          ) : (
            tarea.solicitud_nombre
          )}
        </p>
        <p>
          <strong>Cliente:</strong> {tarea.cliente || "Sin definir"}
        </p>
        <p>
          <strong>Responsable:</strong> {tarea.responsable || "Sin asignar"}
        </p>
        <p>
          <strong>Fechas planeadas:</strong> {tarea.fecha_inicio} a {tarea.fecha_fin}
        </p>
        <p>
          <strong>Fechas reales:</strong> {tarea.fecha_inicio_real ?? "—"} a {tarea.fecha_fin_real ?? "—"}
        </p>
        <p>
          <strong>Horas:</strong> estimadas {tarea.horas_estimadas ?? "—"} · reales {tarea.horas_reales ?? "—"}
        </p>

        <div className="resumen-acciones">
          <button type="button" onClick={() => setMostrarFormularioTarea(true)}>
            Editar Tarea
          </button>
        </div>
      </div>

      <div className="solicitud-detalle-tareas">
        <div className="tabs-nav">
          {[
            { key: "hito", label: "Hito", total: hito ? 1 : 0 },
            { key: "comentarios", label: "Comentarios", total: comentarios.length },
            { key: "enlaces", label: "Enlaces", total: enlaces.length },
          ].map((pestana) => (
            <button
              key={pestana.key}
              type="button"
              className={pestanaActiva === pestana.key ? "tab-activo" : ""}
              onClick={() => setPestanaActiva(pestana.key)}
            >
              {pestana.label} ({pestana.total})
            </button>
          ))}
        </div>

        {pestanaActiva === "hito" && (
          <>
            {!hito && (
              <div className="resumen-acciones">
                <button type="button" onClick={() => setMostrarFormularioHito(true)}>
                  Agregar Hito
                </button>
              </div>
            )}
            {hito ? (
              <div className="hito-card">
                <h4>{hito.nombre}</h4>
                {hito.descripcion && <p>{hito.descripcion}</p>}
                <p className="solicitud-fecha">Vence: {hito.fecha_vencimiento}</p>
                <div className="resumen-acciones">
                  <button type="button" className="secundario" onClick={() => setMostrarFormularioHito(true)}>
                    Editar
                  </button>
                  <button type="button" className="peligro" onClick={() => setMostrarConfirmarBorrarHito(true)}>
                    Borrar
                  </button>
                </div>
              </div>
            ) : (
              <p>Esta tarea todavía no tiene un hito asignado.</p>
            )}
          </>
        )}

        {pestanaActiva === "comentarios" && (
          <>
            <div className="resumen-acciones">
              <button
                type="button"
                onClick={() => {
                  setComentarioEnEdicion(null);
                  setMostrarFormularioComentario(true);
                }}
              >
                Agregar comentario
              </button>
            </div>

            {comentarios.length === 0 && <p>Esta tarea todavía no tiene comentarios.</p>}

            <div className="comentario-lista">
              {comentarios.map((comentario) => (
                <ComentarioItem
                  key={comentario.id}
                  comentario={comentario}
                  onEditar={(c) => {
                    setComentarioEnEdicion(c);
                    setMostrarFormularioComentario(true);
                  }}
                  onBorrar={setComentarioABorrar}
                />
              ))}
            </div>
          </>
        )}

        {pestanaActiva === "enlaces" && (
          <>
            <div className="resumen-acciones">
              <button type="button" onClick={() => setMostrarFormularioEnlace(true)}>
                Agregar enlace
              </button>
            </div>

            {enlaces.length === 0 && <p>Esta tarea todavía no tiene enlaces.</p>}

            <div className="tarea-lista">
              {enlaces.map((enlace) => (
                <EnlaceTareaItem key={enlace.id} enlace={enlace} />
              ))}
            </div>
          </>
        )}
      </div>

      {mostrarFormularioTarea && (
        <div className="modal-overlay" onClick={() => setMostrarFormularioTarea(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>Editar tarea</h3>
            <TareaFormulario
              solicitudId={tarea.solicitud_id}
              tareaInicial={tarea}
              onGuardada={alGuardarTarea}
              onCancelar={() => setMostrarFormularioTarea(false)}
            />
          </div>
        </div>
      )}

      {mostrarFormularioHito && (
        <div className="modal-overlay" onClick={() => setMostrarFormularioHito(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>{hito ? "Editar hito" : "Nuevo hito"}</h3>
            <HitoFormulario
              tareaId={tareaId}
              hitoInicial={hito}
              onGuardado={alGuardarHito}
              onCancelar={() => setMostrarFormularioHito(false)}
            />
          </div>
        </div>
      )}

      {mostrarConfirmarBorrarHito && (
        <ConfirmModal
          titulo="Borrar hito"
          mensaje={`¿Seguro que quieres borrar el hito "${hito.nombre}"?`}
          confirmando={borrandoHito}
          onConfirmar={confirmarBorrarHito}
          onCancelar={() => setMostrarConfirmarBorrarHito(false)}
        />
      )}

      {mostrarFormularioComentario && (
        <div
          className="modal-overlay"
          onClick={() => {
            setMostrarFormularioComentario(false);
            setComentarioEnEdicion(null);
          }}
        >
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>{comentarioEnEdicion ? "Editar comentario" : "Nuevo comentario"}</h3>
            <ComentarioFormulario
              tareaId={tareaId}
              comentarioInicial={comentarioEnEdicion}
              onGuardado={alGuardarComentario}
              onCancelar={() => {
                setMostrarFormularioComentario(false);
                setComentarioEnEdicion(null);
              }}
            />
          </div>
        </div>
      )}

      {comentarioABorrar && (
        <ConfirmModal
          titulo="Borrar comentario"
          mensaje="¿Seguro que quieres borrar este comentario?"
          confirmando={borrandoComentario}
          onConfirmar={confirmarBorrarComentario}
          onCancelar={() => setComentarioABorrar(null)}
        />
      )}

      {mostrarFormularioEnlace && (
        <div className="modal-overlay" onClick={() => setMostrarFormularioEnlace(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>Nuevo enlace</h3>
            <EnlaceTareaFormulario
              tareaId={tareaId}
              onGuardado={alGuardarEnlace}
              onCancelar={() => setMostrarFormularioEnlace(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

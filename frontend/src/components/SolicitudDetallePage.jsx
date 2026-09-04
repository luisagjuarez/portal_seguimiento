import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AdjuntosInput from "./AdjuntosInput.jsx";
import BotonRegresar from "./BotonRegresar.jsx";
import ComentarioItem from "./ComentarioItem.jsx";
import ConfirmModal from "./ConfirmModal.jsx";
import ComentarioSolicitudFormulario from "./ComentarioSolicitudFormulario.jsx";
import EditarSolicitudExternoFormulario from "./EditarSolicitudExternoFormulario.jsx";
import EditarSolicitudFormulario from "./EditarSolicitudFormulario.jsx";
import EnlaceTareaItem from "./EnlaceTareaItem.jsx";
import PrioridadBadge from "./PrioridadBadge.jsx";
import VencimientoBadge from "./VencimientoBadge.jsx";
import TareaFormulario from "./TareaFormulario.jsx";
import TareaItem from "./TareaItem.jsx";
import {
  agregarAdjuntosSolicitud,
  descargarAdjuntoSolicitud,
  eliminarSolicitud,
  eliminarTarea,
  fetchAdjuntosSolicitud,
  fetchComentariosSolicitud,
  fetchEnlacesSolicitud,
  fetchHitosSolicitud,
  fetchSolicitudDetalle,
  fetchTareas,
} from "../api.js";

function formatearTamano(bytes) {
  if (bytes == null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function formatearFechaCorta(iso) {
  try {
    // new Date("2026-08-24") se interpreta en UTC; se arma en horario local para que no
    // se muestre un día antes según el huso horario del navegador.
    const [anio, mes, dia] = iso.split("-").map(Number);
    return new Date(anio, mes - 1, dia).toLocaleDateString("es-MX", { dateStyle: "medium" });
  } catch {
    return iso;
  }
}

export default function SolicitudDetallePage({ esScrumMaster, usuarioActual }) {
  const esExterno = usuarioActual?.codigo_rol_scrum === "EXTERNO";
  const navigate = useNavigate();
  const { id } = useParams();
  const solicitudId = Number(id);
  const onRegresar = () => navigate("/solicitudes");

  const [solicitud, setSolicitud] = useState(null);
  const [tareas, setTareas] = useState([]);
  const [comentarios, setComentarios] = useState([]);
  const [hitos, setHitos] = useState([]);
  const [enlaces, setEnlaces] = useState([]);
  const [adjuntos, setAdjuntos] = useState([]);
  const [descargandoId, setDescargandoId] = useState(null);
  const [nuevosAdjuntos, setNuevosAdjuntos] = useState([]);
  const [subiendoAdjuntos, setSubiendoAdjuntos] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [mostrarEditar, setMostrarEditar] = useState(false);
  const [mostrarConfirmarBorrarSolicitud, setMostrarConfirmarBorrarSolicitud] = useState(false);
  const [borrandoSolicitud, setBorrandoSolicitud] = useState(false);

  const [tareaEnEdicion, setTareaEnEdicion] = useState(null);
  const [mostrarFormularioTarea, setMostrarFormularioTarea] = useState(false);
  const [tareaABorrar, setTareaABorrar] = useState(null);
  const [borrandoTarea, setBorrandoTarea] = useState(false);

  const [pestanaActiva, setPestanaActiva] = useState(esExterno ? "adjuntos" : "tareas");

  const cargarDetalle = () => {
    setCargando(true);
    setError(null);
    // El rol Externo no tiene acceso a nada a nivel tarea (Tareas/Hitos/Enlaces): esas 3
    // llamadas ni se hacen, para no romper el Promise.all con el 403 que devolverían.
    const promesas = esExterno
      ? [fetchSolicitudDetalle(solicitudId), fetchComentariosSolicitud(solicitudId), fetchAdjuntosSolicitud(solicitudId)]
      : [
          fetchSolicitudDetalle(solicitudId),
          fetchTareas(solicitudId),
          fetchComentariosSolicitud(solicitudId),
          fetchHitosSolicitud(solicitudId),
          fetchEnlacesSolicitud(solicitudId),
          fetchAdjuntosSolicitud(solicitudId),
        ];
    Promise.all(promesas)
      .then((resultados) => {
        if (esExterno) {
          const [detalle, listaComentarios, listaAdjuntos] = resultados;
          setSolicitud(detalle);
          setComentarios(listaComentarios);
          setAdjuntos(listaAdjuntos);
        } else {
          const [detalle, listaTareas, listaComentarios, listaHitos, listaEnlaces, listaAdjuntos] = resultados;
          setSolicitud(detalle);
          setTareas(listaTareas);
          setComentarios(listaComentarios);
          setHitos(listaHitos);
          setEnlaces(listaEnlaces);
          setAdjuntos(listaAdjuntos);
        }
      })
      .catch((err) => setError(err.message || "No se pudo cargar el detalle de la solicitud."))
      .finally(() => setCargando(false));
  };

  const descargarAdjunto = async (adjunto) => {
    setDescargandoId(adjunto.id);
    try {
      await descargarAdjuntoSolicitud(solicitudId, adjunto.id, adjunto.nombre_archivo);
    } catch (err) {
      setError(err.message || "No se pudo descargar el adjunto.");
    } finally {
      setDescargandoId(null);
    }
  };

  const subirAdjuntos = async () => {
    if (nuevosAdjuntos.length === 0) return;
    setSubiendoAdjuntos(true);
    setError(null);
    try {
      const agregados = await agregarAdjuntosSolicitud(solicitudId, nuevosAdjuntos);
      setAdjuntos((actuales) => [...actuales, ...agregados]);
      setNuevosAdjuntos([]);
    } catch (err) {
      setError(err.message || "No se pudieron subir los adjuntos.");
    } finally {
      setSubiendoAdjuntos(false);
    }
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
        <BotonRegresar onClick={onRegresar}>Regresar</BotonRegresar>
      </div>
    );
  }

  // Fase 1.18/nuevo ajuste: el responsable de atención asignado a la solicitud también puede
  // crear tareas y asignarlas a cualquier miembro del equipo, sin importar su rol Scrum.
  const esResponsableAtencion =
    usuarioActual != null && usuarioActual.id === solicitud.responsable_atencion_id;
  const puedeCrearTarea = esScrumMaster || esResponsableAtencion;

  return (
    <div className="solicitud-detalle-page">
      <BotonRegresar onClick={onRegresar}>Regresar</BotonRegresar>

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
        <p>
          <strong>Canal:</strong> {solicitud.canal || "Sin definir"}
        </p>
        {solicitud.sr_ebs && (
          <p>
            <strong>SR de EBS:</strong> {solicitud.sr_ebs}
          </p>
        )}
        <p>
          <strong>Prioridad:</strong>{" "}
          <PrioridadBadge nivel={solicitud.orden_prioridad} codigoEstatus={solicitud.codigo_estatus} />
        </p>
        {solicitud.responsable_atencion && (
          <p>
            <strong>Responsable de atención:</strong> {solicitud.responsable_atencion} (
            {solicitud.responsable_atencion_area})
          </p>
        )}
        {solicitud.fecha_entrega && (
          <p>
            <strong>Fecha de entrega:</strong>{" "}
            <VencimientoBadge fechaEntrega={solicitud.fecha_entrega} codigoEstatus={solicitud.codigo_estatus} />
          </p>
        )}
        {solicitud.codigo_estatus === "COMPLETADO" && solicitud.fecha_completado && (
          <p>
            <strong>Fecha Completado:</strong> {formatearFechaCorta(solicitud.fecha_completado)}
          </p>
        )}
        <p className="solicitud-fecha">Creada: {formatearFecha(solicitud.creado_en)}</p>

        <div className="resumen-acciones">
          {(!esExterno || solicitud.codigo_estatus === "EN ESPERA") && (
            <button type="button" onClick={() => setMostrarEditar(true)}>
              Editar Solicitud
            </button>
          )}
          {esScrumMaster && (
            <button type="button" className="peligro" onClick={() => setMostrarConfirmarBorrarSolicitud(true)}>
              Borrar Solicitud
            </button>
          )}
        </div>
        {esExterno && solicitud.codigo_estatus !== "EN ESPERA" && (
          <p className="adjuntos-ayuda">Solo puedes editar la solicitud mientras está En espera.</p>
        )}
      </div>

      <div className="solicitud-detalle-tareas">
        <div className="tabs-nav">
          {[
            { key: "adjuntos", label: "Adjuntos", total: adjuntos.length },
            !esExterno && { key: "tareas", label: "Tareas", total: tareas.length },
            { key: "comentarios", label: "Comentarios", total: comentarios.length },
            !esExterno && { key: "hitos", label: "Hitos", total: hitos.length },
            !esExterno && { key: "enlaces", label: "Enlaces de tareas", total: enlaces.length },
          ]
            .filter(Boolean)
            .map((pestana) => (
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

        {pestanaActiva === "adjuntos" && (
          <>
            {adjuntos.length === 0 && <p>Esta solicitud todavía no tiene adjuntos.</p>}
            <ul className="adjuntos-lista">
              {adjuntos.map((adjunto) => (
                <li key={adjunto.id}>
                  <span>
                    {adjunto.nombre_archivo}
                    {adjunto.tamano_bytes != null && ` (${formatearTamano(adjunto.tamano_bytes)})`}
                  </span>
                  <button
                    type="button"
                    className="secundario"
                    disabled={descargandoId === adjunto.id}
                    onClick={() => descargarAdjunto(adjunto)}
                  >
                    {descargandoId === adjunto.id ? "Descargando..." : "Descargar"}
                  </button>
                </li>
              ))}
            </ul>

            <div className="adjuntos-agregar">
              <p className="crear-solicitud-etiqueta">Agregar adjuntos</p>
              <AdjuntosInput archivos={nuevosAdjuntos} onChange={setNuevosAdjuntos} />
              <button
                type="button"
                disabled={nuevosAdjuntos.length === 0 || subiendoAdjuntos}
                onClick={subirAdjuntos}
              >
                {subiendoAdjuntos ? "Subiendo..." : "Subir adjuntos"}
              </button>
            </div>
          </>
        )}

        {pestanaActiva === "tareas" && (
          <>
            {puedeCrearTarea ? (
              <div className="resumen-acciones">
                <button
                  type="button"
                  onClick={() => {
                    setTareaEnEdicion(null);
                    setMostrarFormularioTarea(true);
                  }}
                >
                  Agregar Tarea
                </button>
              </div>
            ) : (
              <p className="adjuntos-ayuda">
                Solo el Scrum Master o el responsable de atención de la solicitud pueden agregar tareas.
              </p>
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
                  onBorrar={esScrumMaster ? setTareaABorrar : undefined}
                  onAbrirDetalle={(tareaId) => navigate(`/tareas/${tareaId}`)}
                />
              ))}
            </div>
          </>
        )}

        {pestanaActiva === "comentarios" && (
          <>
            <ComentarioSolicitudFormulario
              solicitudId={solicitudId}
              onGuardado={(comentario) => setComentarios((actuales) => [...actuales, comentario])}
            />
            {comentarios.length === 0 && <p>Ninguna tarea de esta solicitud tiene comentarios todavía.</p>}
            <div className="comentario-lista">
              {comentarios.map((comentario) => (
                <ComentarioItem key={comentario.id} comentario={comentario} mostrarTarea />
              ))}
            </div>
          </>
        )}

        {pestanaActiva === "hitos" && (
          <>
            {hitos.length === 0 && <p>Ninguna tarea de esta solicitud tiene hitos todavía.</p>}
            <div className="tarea-lista">
              {hitos.map((hito) => (
                <div key={hito.id} className="hito-card">
                  <h4>{hito.nombre}</h4>
                  {hito.descripcion && <p>{hito.descripcion}</p>}
                  {hito.tarea_nombre && <p className="solicitud-fecha">Tarea: {hito.tarea_nombre}</p>}
                  <p className="solicitud-fecha">Vence: {hito.fecha_vencimiento}</p>
                  <p className="solicitud-fecha">Responsable: {hito.creado_por_nombre}</p>
                </div>
              ))}
            </div>
          </>
        )}

        {pestanaActiva === "enlaces" && (
          <>
            {enlaces.length === 0 && <p>Ninguna tarea de esta solicitud tiene enlaces todavía.</p>}
            <div className="tarea-lista">
              {enlaces.map((enlace) => (
                <EnlaceTareaItem key={enlace.id} enlace={enlace} mostrarTarea />
              ))}
            </div>
          </>
        )}
      </div>

      {mostrarEditar && (
        <div className="modal-overlay" onClick={() => setMostrarEditar(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>Editar solicitud</h3>
            {esExterno ? (
              <EditarSolicitudExternoFormulario
                solicitud={solicitud}
                onActualizada={alActualizarSolicitud}
                onCancelar={() => setMostrarEditar(false)}
              />
            ) : (
              <EditarSolicitudFormulario
                solicitud={solicitud}
                onActualizada={alActualizarSolicitud}
                onCancelar={() => setMostrarEditar(false)}
              />
            )}
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

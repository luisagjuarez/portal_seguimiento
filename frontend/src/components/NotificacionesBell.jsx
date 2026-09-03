import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchNotificaciones,
  fetchNotificacionesNoLeidasCount,
  marcarNotificacionLeida,
  marcarTodasNotificacionesLeidas,
} from "../api.js";

const INTERVALO_POLL_MS = 30000;

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function rutaDeNotificacion(notificacion) {
  if (notificacion.entidad_tipo === "TAREA") {
    return `/tareas/${notificacion.entidad_id}`;
  }
  if (notificacion.entidad_tipo === "SOLICITUD") {
    return `/solicitudes/${notificacion.entidad_id}`;
  }
  return null;
}

export default function NotificacionesBell() {
  const navigate = useNavigate();
  const [noLeidas, setNoLeidas] = useState(0);
  const [abierto, setAbierto] = useState(false);
  const [notificaciones, setNotificaciones] = useState([]);
  const [cargando, setCargando] = useState(false);

  const actualizarConteo = () => {
    fetchNotificacionesNoLeidasCount()
      .then((data) => setNoLeidas(data.no_leidas))
      .catch(() => {
        /* si falla el poll, simplemente se reintenta en el siguiente ciclo */
      });
  };

  useEffect(() => {
    actualizarConteo();
    const intervalId = setInterval(actualizarConteo, INTERVALO_POLL_MS);
    return () => clearInterval(intervalId);
  }, []);

  const alAbrir = () => {
    const nuevoEstado = !abierto;
    setAbierto(nuevoEstado);
    if (nuevoEstado) {
      setCargando(true);
      fetchNotificaciones()
        .then(setNotificaciones)
        .catch(() => setNotificaciones([]))
        .finally(() => setCargando(false));
    }
  };

  const alHacerClicNotificacion = async (notificacion) => {
    if (!notificacion.leido_en) {
      setNotificaciones((actuales) =>
        actuales.map((n) => (n.id === notificacion.id ? { ...n, leido_en: new Date().toISOString() } : n)),
      );
      setNoLeidas((actual) => Math.max(0, actual - 1));
      marcarNotificacionLeida(notificacion.id).catch(() => {
        /* la próxima carga de la lista corrige el estado si esto falla */
      });
    }
    setAbierto(false);
    const ruta = rutaDeNotificacion(notificacion);
    if (ruta) {
      navigate(ruta);
    }
  };

  const alMarcarTodasLeidas = async () => {
    setNotificaciones((actuales) => actuales.map((n) => ({ ...n, leido_en: n.leido_en || new Date().toISOString() })));
    setNoLeidas(0);
    try {
      await marcarTodasNotificacionesLeidas();
    } catch {
      /* no crítico: el conteo se corrige en el próximo poll */
    }
  };

  return (
    <div className="notificaciones-bell-wrap">
      <button
        type="button"
        className="theme-toggle notificaciones-bell-boton"
        onClick={alAbrir}
        aria-label="Notificaciones"
        title="Notificaciones"
      >
        🔔
        {noLeidas > 0 && <span className="notificaciones-badge">{noLeidas > 99 ? "99+" : noLeidas}</span>}
      </button>

      {abierto && (
        <div className="notificaciones-panel">
          <div className="notificaciones-panel-encabezado">
            <strong>Notificaciones</strong>
            {noLeidas > 0 && (
              <button type="button" className="enlace" onClick={alMarcarTodasLeidas}>
                Marcar todas como leídas
              </button>
            )}
          </div>
          {cargando && <p>Cargando...</p>}
          {!cargando && notificaciones.length === 0 && <p>No tienes notificaciones.</p>}
          <ul className="notificaciones-lista">
            {notificaciones.map((notificacion) => (
              <li key={notificacion.id}>
                <button
                  type="button"
                  className={notificacion.leido_en ? "notificacion-item" : "notificacion-item notificacion-no-leida"}
                  onClick={() => alHacerClicNotificacion(notificacion)}
                >
                  <span className="notificacion-mensaje">{notificacion.mensaje}</span>
                  <span className="notificacion-fecha">{formatearFecha(notificacion.creado_en)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

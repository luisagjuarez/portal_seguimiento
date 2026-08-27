import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RELLENO_POR_ESTATUS } from "../constants/estatusTarea.js";
import { fetchMonitorKpis } from "../api.js";

function TablaTareas({ tareas, columnaDias, claseDias, navigate }) {
  return (
    <table className="tabla-usuarios">
      <thead>
        <tr>
          <th>Tarea</th>
          <th>Solicitud</th>
          <th>Cliente</th>
          <th>Responsable</th>
          <th>Vence</th>
          <th>{columnaDias}</th>
        </tr>
      </thead>
      <tbody>
        {tareas.map((tarea) => (
          <tr key={tarea.id}>
            <td>
              <button type="button" className="enlace" onClick={() => navigate(`/tareas/${tarea.id}`)}>
                {tarea.nombre}
              </button>
            </td>
            <td>{tarea.solicitud_nombre}</td>
            <td>{tarea.cliente || "Sin definir"}</td>
            <td>{tarea.responsable || "Sin asignar"}</td>
            <td>{tarea.fecha_fin}</td>
            <td className={claseDias}>{tarea.dias}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function MonitorPage() {
  const navigate = useNavigate();
  const [kpis, setKpis] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMonitorKpis()
      .then(setKpis)
      .catch((err) => setError(err.message || "No se pudo cargar el monitor."))
      .finally(() => setCargando(false));
  }, []);

  if (cargando) {
    return <p>Cargando monitor...</p>;
  }

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  const maxCarga = Math.max(1, ...kpis.carga_por_responsable.map((c) => c.tareas_abiertas));
  const maxDistribucion = Math.max(1, ...kpis.distribucion_estatus.map((d) => d.total));
  const { cumplimiento } = kpis;

  return (
    <div className="monitor-page">
      <div className="solicitudes-encabezado">
        <h2>Monitor de tareas</h2>
      </div>

      <div className="monitor-stats">
        <div className="monitor-stat-tile">
          <span className="monitor-stat-valor">{kpis.vencidas.length}</span>
          <span className="monitor-stat-etiqueta">Tareas vencidas</span>
        </div>
        <div className="monitor-stat-tile">
          <span className="monitor-stat-valor">{kpis.por_vencer.length}</span>
          <span className="monitor-stat-etiqueta">Por vencer (7 días)</span>
        </div>
        <div className="monitor-stat-tile">
          <span className="monitor-stat-valor">
            {cumplimiento.porcentaje_cumplimiento != null ? `${cumplimiento.porcentaje_cumplimiento}%` : "—"}
          </span>
          <span className="monitor-stat-etiqueta">Cumplimiento de fechas</span>
        </div>
      </div>

      <div className="monitor-section">
        <h3>Tareas vencidas ({kpis.vencidas.length})</h3>
        {kpis.vencidas.length === 0 ? (
          <p>No hay tareas vencidas.</p>
        ) : (
          <TablaTareas
            tareas={kpis.vencidas}
            columnaDias="Días de atraso"
            claseDias="monitor-dias-vencida"
            navigate={navigate}
          />
        )}
      </div>

      <div className="monitor-section">
        <h3>Por vencer en los próximos 7 días ({kpis.por_vencer.length})</h3>
        {kpis.por_vencer.length === 0 ? (
          <p>No hay tareas por vencer en los próximos 7 días.</p>
        ) : (
          <TablaTareas
            tareas={kpis.por_vencer}
            columnaDias="Días restantes"
            claseDias="monitor-dias-por-vencer"
            navigate={navigate}
          />
        )}
      </div>

      <div className="monitor-section">
        <h3>Carga por responsable</h3>
        {kpis.carga_por_responsable.map((c) => (
          <div className="monitor-bar-row" key={c.responsable_id ?? "sin-asignar"}>
            <span className="monitor-bar-etiqueta">{c.responsable || "Sin asignar"}</span>
            <div className="monitor-bar-track">
              <div
                className="monitor-bar-fill"
                style={{ width: `${(c.tareas_abiertas / maxCarga) * 100}%` }}
              />
            </div>
            <span className="monitor-bar-valor">{c.tareas_abiertas}</span>
          </div>
        ))}
      </div>

      <div className="monitor-section">
        <h3>Distribución por estatus</h3>
        {kpis.distribucion_estatus.map((d) => (
          <div className="monitor-bar-row" key={d.codigo_estatus_tarea}>
            <span className="monitor-bar-etiqueta">{d.descripcion}</span>
            <div className="monitor-bar-track">
              <div
                className={`monitor-bar-fill ${RELLENO_POR_ESTATUS[d.codigo_estatus_tarea] || ""}`}
                style={{ width: `${(d.total / maxDistribucion) * 100}%` }}
              />
            </div>
            <span className="monitor-bar-valor">{d.total}</span>
          </div>
        ))}
      </div>

      <div className="monitor-section">
        <h3>Cumplimiento planeado vs. real</h3>
        {cumplimiento.total_con_fecha_real === 0 ? (
          <p>Todavía no hay tareas completadas con fecha real registrada.</p>
        ) : (
          <>
            <div className="monitor-bar-track monitor-bar-track-cumplimiento">
              <div
                className="monitor-bar-fill monitor-bar-cumplida"
                style={{ width: `${(cumplimiento.cumplidas / cumplimiento.total_con_fecha_real) * 100}%` }}
              />
              <div
                className="monitor-bar-fill monitor-bar-atrasada"
                style={{ width: `${(cumplimiento.atrasadas / cumplimiento.total_con_fecha_real) * 100}%` }}
              />
            </div>
            <p>
              {cumplimiento.cumplidas} cumplidas · {cumplimiento.atrasadas} atrasadas
              {cumplimiento.promedio_dias_atraso != null &&
                ` (promedio ${cumplimiento.promedio_dias_atraso} días de atraso)`}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

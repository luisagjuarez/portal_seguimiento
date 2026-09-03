import { useEffect, useState } from "react";
import DireccionGeneralDetalleMetrica from "./DireccionGeneralDetalleMetrica.jsx";
import { CLASE_POR_ESTATUS } from "../constants/estatusTarea.js";
import { fetchDireccionGeneralKpis } from "../api.js";

const ETIQUETA_POR_METRICA = {
  en_proceso: "Solicitudes en proceso",
  concluidas: "Solicitudes concluidas",
  nuevas: "Nuevas solicitudes",
};

function primerDiaDelMes() {
  const hoy = new Date();
  return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, "0")}-01`;
}

function hoyISO() {
  return new Date().toISOString().slice(0, 10);
}

function TablaGrupo({ titulo, etiquetaColumna, filas }) {
  return (
    <div className="monitor-section">
      <h3>{titulo}</h3>
      {filas.length === 0 ? (
        <p>Sin datos en este rango.</p>
      ) : (
        <div className="tabla-scroll">
          <table className="tabla-usuarios">
            <thead>
              <tr>
                <th rowSpan={2}>{etiquetaColumna}</th>
                <th colSpan={3}>Solicitudes</th>
                <th colSpan={4}>Tareas</th>
              </tr>
              <tr>
                <th>En proceso</th>
                <th>Concluidas</th>
                <th>Nuevas</th>
                <th>En proceso</th>
                <th>Concluidas</th>
                <th>Nuevas</th>
                <th>Horas est.</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <tr key={f.grupo_id ?? f.grupo}>
                  <td>{f.grupo}</td>
                  <td className="celda-numero">{f.solicitudes_en_proceso}</td>
                  <td className="celda-numero">{f.solicitudes_concluidas_periodo}</td>
                  <td className="celda-numero">{f.solicitudes_nuevas_periodo}</td>
                  <td className="celda-numero">{f.tareas_en_proceso}</td>
                  <td className="celda-numero">{f.tareas_concluidas_periodo}</td>
                  <td className="celda-numero">{f.tareas_nuevas_periodo}</td>
                  <td className="celda-numero">{f.horas_estimadas_periodo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TablaEstatus({ titulo, filas, codigoClave, claseBadge }) {
  return (
    <div className="monitor-section">
      <h3>{titulo}</h3>
      <table className="tabla-usuarios">
        <thead>
          <tr>
            <th>Estatus</th>
            <th>Cantidad</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => (
            <tr key={f[codigoClave]}>
              <td>
                {claseBadge ? (
                  <span className={`tarea-estado ${claseBadge[f[codigoClave]] || ""}`}>{f.descripcion}</span>
                ) : (
                  f.descripcion
                )}
              </td>
              <td className="celda-numero">{f.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function DireccionGeneralPage() {
  const [desde, setDesde] = useState(primerDiaDelMes);
  const [hasta, setHasta] = useState(hoyISO);
  const [kpis, setKpis] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [metricaSeleccionada, setMetricaSeleccionada] = useState(null);

  useEffect(() => {
    setCargando(true);
    setError(null);
    fetchDireccionGeneralKpis(desde, hasta)
      .then(setKpis)
      .catch((err) => setError(err.message || "No se pudo cargar el tablero."))
      .finally(() => setCargando(false));
  }, [desde, hasta]);

  if (metricaSeleccionada) {
    return (
      <div className="monitor-page">
        <div className="solicitudes-encabezado">
          <h2>Dirección General</h2>
        </div>
        <DireccionGeneralDetalleMetrica
          metrica={metricaSeleccionada}
          etiquetaMetrica={ETIQUETA_POR_METRICA[metricaSeleccionada]}
          desde={desde}
          hasta={hasta}
          onVolver={() => setMetricaSeleccionada(null)}
        />
      </div>
    );
  }

  return (
    <div className="monitor-page">
      <div className="solicitudes-encabezado">
        <h2>Dirección General</h2>
        <div className="direccion-general-rango">
          <label>
            Desde
            <input type="date" value={desde} max={hasta} onChange={(e) => setDesde(e.target.value)} />
          </label>
          <label>
            Hasta
            <input type="date" value={hasta} min={desde} onChange={(e) => setHasta(e.target.value)} />
          </label>
        </div>
      </div>

      {cargando && <p>Cargando...</p>}
      {error && <p className="error-text">{error}</p>}

      {kpis && !cargando && (
        <>
          <div className="monitor-stats">
            <button
              type="button"
              className="monitor-stat-tile monitor-stat-tile--clicable"
              onClick={() => setMetricaSeleccionada("en_proceso")}
            >
              <span className="monitor-stat-valor">{kpis.totales.solicitudes_en_proceso}</span>
              <span className="monitor-stat-etiqueta">Solicitudes en proceso</span>
            </button>
            <div className="monitor-stat-tile">
              <span className="monitor-stat-valor">{kpis.totales.tareas_en_proceso}</span>
              <span className="monitor-stat-etiqueta">Tareas en proceso</span>
            </div>
            <button
              type="button"
              className="monitor-stat-tile monitor-stat-tile--clicable"
              onClick={() => setMetricaSeleccionada("concluidas")}
            >
              <span className="monitor-stat-valor">{kpis.totales.solicitudes_concluidas_periodo}</span>
              <span className="monitor-stat-etiqueta">Solicitudes concluidas</span>
            </button>
            <div className="monitor-stat-tile">
              <span className="monitor-stat-valor">{kpis.totales.tareas_concluidas_periodo}</span>
              <span className="monitor-stat-etiqueta">Tareas concluidas</span>
            </div>
            <button
              type="button"
              className="monitor-stat-tile monitor-stat-tile--clicable"
              onClick={() => setMetricaSeleccionada("nuevas")}
            >
              <span className="monitor-stat-valor">{kpis.totales.solicitudes_nuevas_periodo}</span>
              <span className="monitor-stat-etiqueta">Nuevas solicitudes</span>
            </button>
            <div className="monitor-stat-tile">
              <span className="monitor-stat-valor">{kpis.totales.tareas_nuevas_periodo}</span>
              <span className="monitor-stat-etiqueta">Nuevas tareas</span>
            </div>
            <div className="monitor-stat-tile">
              <span className="monitor-stat-valor">{kpis.totales.horas_estimadas_periodo}</span>
              <span className="monitor-stat-etiqueta">Horas estimadas</span>
            </div>
          </div>

          <TablaGrupo titulo="Por cliente" etiquetaColumna="Cliente" filas={kpis.por_cliente} />
          <TablaGrupo titulo="Por tipo de solicitud" etiquetaColumna="Tipo" filas={kpis.por_tipo} />
          <TablaGrupo titulo="Por área" etiquetaColumna="Área" filas={kpis.por_area} />

          <TablaEstatus
            titulo="Solicitudes por estatus"
            filas={kpis.solicitudes_por_estatus}
            codigoClave="codigo_estatus"
          />
          <TablaEstatus
            titulo="Tareas por estatus"
            filas={kpis.tareas_por_estatus}
            codigoClave="codigo_estatus_tarea"
            claseBadge={CLASE_POR_ESTATUS}
          />
        </>
      )}
    </div>
  );
}

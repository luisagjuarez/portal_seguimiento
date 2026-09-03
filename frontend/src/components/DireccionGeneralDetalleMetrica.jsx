import { useEffect, useState } from "react";
import PieChart from "./PieChart.jsx";
import { fetchDireccionGeneralDetalleSolicitudes } from "../api.js";

const COLORES_SERIE = [
  "var(--chart-series-1)",
  "var(--chart-series-2)",
  "var(--chart-series-3)",
  "var(--chart-series-4)",
  "var(--chart-series-5)",
];
const COLOR_OTROS = "var(--chart-otros)";
const TOP_N = 5;

function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function agruparTop5(filas, campo) {
  const conteos = new Map();
  for (const fila of filas) {
    const clave = fila[campo] || "Sin dato";
    conteos.set(clave, (conteos.get(clave) || 0) + 1);
  }
  const ordenado = [...conteos.entries()].sort((a, b) => b[1] - a[1]);
  const principales = ordenado.slice(0, TOP_N).map(([label, value], i) => ({
    label,
    value,
    color: COLORES_SERIE[i],
  }));
  const resto = ordenado.slice(TOP_N).reduce((suma, [, value]) => suma + value, 0);
  if (resto > 0) {
    principales.push({ label: "Otros", value: resto, color: COLOR_OTROS });
  }
  return principales;
}

export default function DireccionGeneralDetalleMetrica({ metrica, etiquetaMetrica, desde, hasta, onVolver }) {
  const [filas, setFilas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setCargando(true);
    setError(null);
    fetchDireccionGeneralDetalleSolicitudes(metrica, desde, hasta)
      .then(setFilas)
      .catch((err) => setError(err.message || "No se pudo cargar el detalle."))
      .finally(() => setCargando(false));
  }, [metrica, desde, hasta]);

  return (
    <div className="direccion-general-detalle">
      <button type="button" className="secundario" onClick={onVolver}>
        ← Volver
      </button>

      {cargando && <p>Cargando...</p>}
      {error && <p className="error-text">{error}</p>}

      {!cargando && !error && (
        <>
          <div className="monitor-stats">
            <div className="monitor-stat-tile">
              <span className="monitor-stat-valor">{filas.length}</span>
              <span className="monitor-stat-etiqueta">{etiquetaMetrica}</span>
            </div>
          </div>

          <div className="direccion-general-pies">
            <PieChart titulo="Por cliente" data={agruparTop5(filas, "cliente")} />
            <PieChart titulo="Por área" data={agruparTop5(filas, "area")} />
          </div>

          <div className="monitor-section">
            <h3>Solicitudes</h3>
            {filas.length === 0 ? (
              <p>Sin datos en este rango.</p>
            ) : (
              <div className="tabla-scroll">
                <table className="tabla-usuarios">
                  <thead>
                    <tr>
                      <th>Nombre de la solicitud</th>
                      <th>Cliente</th>
                      <th>Fecha de solicitud</th>
                      <th>Solicitante</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filas.map((fila) => (
                      <tr key={fila.id}>
                        <td>{fila.nombre}</td>
                        <td>{fila.cliente || "—"}</td>
                        <td>{formatearFecha(fila.creado_en)}</td>
                        <td>{fila.solicitante || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

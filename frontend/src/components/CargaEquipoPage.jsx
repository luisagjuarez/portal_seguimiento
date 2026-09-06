import { useCallback, useEffect, useState } from "react";
import MiembroCargaBox from "./MiembroCargaBox.jsx";
import TareaCargaBox from "./TareaCargaBox.jsx";
import { fetchCargaEquipo } from "../api.js";

const INTERVALO_REFRESCO_MS = 5 * 60 * 1000; // 5 minutos

export default function CargaEquipoPage() {
  const [areas, setAreas] = useState([]);
  const [ultimaActualizacion, setUltimaActualizacion] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const cargar = useCallback(() => {
    setError(null);
    fetchCargaEquipo()
      .then((datos) => {
        setAreas(datos);
        setUltimaActualizacion(new Date());
      })
      .catch((err) => setError(err.message || "No se pudo cargar la carga del equipo."))
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    cargar();
    const intervalId = setInterval(cargar, INTERVALO_REFRESCO_MS);
    return () => clearInterval(intervalId);
  }, [cargar]);

  return (
    <div className="carga-equipo-page">
      <div className="solicitudes-encabezado">
        <h2>Tareas en proceso</h2>
      </div>

      <div className="carga-equipo-leyenda">
        <span>
          Última actualización:{" "}
          {ultimaActualizacion ? ultimaActualizacion.toLocaleString("es-MX") : "Cargando..."}
        </span>
        <button type="button" className="secundario" onClick={cargar}>
          Actualizar ahora
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}
      {cargando && <p>Cargando carga del equipo...</p>}

      {!cargando &&
        areas.map((areaInfo) => (
          <div className="carga-equipo-area" key={areaInfo.area}>
            <h3>{areaInfo.area}</h3>
            <div className="tabla-usuarios-wrap">
              <table className="tabla-usuarios">
                <thead>
                  <tr>
                    <th className="carga-equipo-th-centrado">Miembro del equipo</th>
                    <th className="carga-equipo-th-centrado">Tarea 1</th>
                    <th className="carga-equipo-th-centrado">Tarea 2</th>
                    <th className="carga-equipo-th-centrado">Tarea 3</th>
                  </tr>
                </thead>
                <tbody>
                  {areaInfo.miembros.map((miembro) => (
                    <tr key={miembro.id}>
                      <td>
                        <MiembroCargaBox miembro={miembro} />
                      </td>
                      {[0, 1, 2].map((indice) =>
                        miembro.tareas[indice] ? (
                          <td key={indice}>
                            <TareaCargaBox tarea={miembro.tareas[indice]} />
                          </td>
                        ) : (
                          <td key={indice} className="carga-equipo-sin-tarea">
                            Sin tarea
                          </td>
                        ),
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
    </div>
  );
}

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PRIORIDAD_INFO } from "../constants/prioridad.js";
import { fetchInicioResumen } from "../api.js";

function BloqueResumen({ titulo, bloque }) {
  const maxEstatus = Math.max(1, ...bloque.por_estatus.map((f) => f.total));

  return (
    <div className="monitor-section inicio-bloque">
      <h3>
        {titulo} ({bloque.total})
      </h3>

      <div className="inicio-prioridad-fila">
        {bloque.por_prioridad.map((fila) => (
          <span key={fila.valor} className={`prioridad-badge prioridad-${fila.valor} inicio-prioridad-pildora`}>
            {PRIORIDAD_INFO[fila.valor]?.etiqueta || fila.descripcion}: {fila.total}
          </span>
        ))}
      </div>

      {bloque.por_estatus.map((fila) => (
        <div className="monitor-bar-row" key={fila.valor}>
          <span className="monitor-bar-etiqueta">{fila.descripcion}</span>
          <div className="monitor-bar-track">
            <div className="monitor-bar-fill" style={{ width: `${(fila.total / maxEstatus) * 100}%` }} />
          </div>
          <span className="monitor-bar-valor">{fila.total}</span>
        </div>
      ))}
    </div>
  );
}

export default function InicioPage({ usuarioActual }) {
  const navigate = useNavigate();
  const [resumen, setResumen] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchInicioResumen()
      .then(setResumen)
      .catch((err) => setError(err.message || "No se pudo cargar el resumen."));
  }, []);

  return (
    <div className="inicio-page">
      <h2>Bienvenido, {usuarioActual?.nombre_completo}</h2>
      <p>
        Este es el Portal de Seguimiento DOVELA. Desde aquí puedes registrar y consultar las
        solicitudes de los equipos de tecnología de DOVELA (Fábrica de Software, Implementación,
        Mesa de Ayuda, Infraestructura, Sysadmins &amp; DBAs).
      </p>
      <div className="inicio-acciones">
        <button type="button" onClick={() => navigate("/chat")}>
          Registrar solicitud por chat
        </button>
        <button type="button" className="secundario" onClick={() => navigate("/solicitudes")}>
          Ver solicitudes existentes
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {resumen && (
        <div className="inicio-dashboard">
          {resumen.solicitudes_totales && (
            <BloqueResumen titulo="Solicitudes totales" bloque={resumen.solicitudes_totales} />
          )}
          {resumen.tareas_totales && <BloqueResumen titulo="Tareas totales" bloque={resumen.tareas_totales} />}
          {resumen.mis_solicitudes && (
            <BloqueResumen titulo="Mis solicitudes" bloque={resumen.mis_solicitudes} />
          )}
          {resumen.solicitudes_responsable && (
            <BloqueResumen titulo="Solicitudes que atiendo" bloque={resumen.solicitudes_responsable} />
          )}
          {resumen.mis_tareas && <BloqueResumen titulo="Mis tareas" bloque={resumen.mis_tareas} />}
        </div>
      )}
    </div>
  );
}

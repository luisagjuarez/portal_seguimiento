import { useNavigate } from "react-router-dom";

export default function InicioPage({ usuarioActual }) {
  const navigate = useNavigate();

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
    </div>
  );
}

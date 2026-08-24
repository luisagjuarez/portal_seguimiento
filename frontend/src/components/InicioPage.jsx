export default function InicioPage({ onIrA }) {
  return (
    <div className="inicio-page">
      <h2>Bienvenido al Portal de Seguimiento DOVELA</h2>
      <p>
        Desde aquí puedes registrar y consultar las solicitudes de los equipos de tecnología de
        DOVELA (Fábrica de Software, Implementación, Mesa de Ayuda, Infraestructura, Sysadmins
        &amp; DBAs).
      </p>
      <div className="inicio-acciones">
        <button type="button" onClick={() => onIrA("chat")}>
          Registrar solicitud por chat
        </button>
        <button type="button" className="secundario" onClick={() => onIrA("solicitudes")}>
          Ver solicitudes existentes
        </button>
      </div>
    </div>
  );
}

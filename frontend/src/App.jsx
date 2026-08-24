import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import InicioPage from "./components/InicioPage.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import SolicitudesPage from "./components/SolicitudesPage.jsx";
import SolicitudDetallePage from "./components/SolicitudDetallePage.jsx";

export default function App() {
  const [pagina, setPagina] = useState("inicio");
  const [solicitudSeleccionadaId, setSolicitudSeleccionadaId] = useState(null);

  const verDetalleSolicitud = (id) => {
    setSolicitudSeleccionadaId(id);
    setPagina("solicitud-detalle");
  };

  const regresarASolicitudes = () => {
    setSolicitudSeleccionadaId(null);
    setPagina("solicitudes");
  };

  return (
    <div className="app-layout">
      <Sidebar paginaActual={pagina} onCambiarPagina={setPagina} />
      <div className="main-content">
        <header>
          <h1>Portal de Seguimiento DOVELA</h1>
        </header>
        <main>
          {pagina === "inicio" && <InicioPage onIrA={setPagina} />}
          {pagina === "chat" && <ChatWindow />}
          {pagina === "solicitudes" && <SolicitudesPage onVerDetalle={verDetalleSolicitud} />}
          {pagina === "solicitud-detalle" && (
            <SolicitudDetallePage solicitudId={solicitudSeleccionadaId} onRegresar={regresarASolicitudes} />
          )}
        </main>
      </div>
    </div>
  );
}

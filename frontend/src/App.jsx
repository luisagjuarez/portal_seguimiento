import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import InicioPage from "./components/InicioPage.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import SolicitudesPage from "./components/SolicitudesPage.jsx";
import SolicitudDetallePage from "./components/SolicitudDetallePage.jsx";
import TareaDetallePage from "./components/TareaDetallePage.jsx";
import TableroPage from "./components/TableroPage.jsx";

export default function App() {
  const [pagina, setPagina] = useState("inicio");
  const [solicitudSeleccionadaId, setSolicitudSeleccionadaId] = useState(null);
  const [tareaSeleccionadaId, setTareaSeleccionadaId] = useState(null);
  const [origenTarea, setOrigenTarea] = useState("solicitud");

  const verDetalleSolicitud = (id) => {
    setSolicitudSeleccionadaId(id);
    setPagina("solicitud-detalle");
  };

  const regresarASolicitudes = () => {
    setSolicitudSeleccionadaId(null);
    setPagina("solicitudes");
  };

  const verDetalleTareaDesdeSolicitud = (id) => {
    setTareaSeleccionadaId(id);
    setOrigenTarea("solicitud");
    setPagina("tarea-detalle");
  };

  const verDetalleTareaDesdeTablero = (id) => {
    setTareaSeleccionadaId(id);
    setOrigenTarea("tablero");
    setPagina("tarea-detalle");
  };

  const regresarDeTareaDetalle = () => {
    setTareaSeleccionadaId(null);
    setPagina(origenTarea === "tablero" ? "tablero" : "solicitud-detalle");
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
            <SolicitudDetallePage
              solicitudId={solicitudSeleccionadaId}
              onRegresar={regresarASolicitudes}
              onVerTarea={verDetalleTareaDesdeSolicitud}
            />
          )}
          {pagina === "tablero" && <TableroPage onVerTarea={verDetalleTareaDesdeTablero} />}
          {pagina === "tarea-detalle" && (
            <TareaDetallePage tareaId={tareaSeleccionadaId} onRegresar={regresarDeTareaDetalle} />
          )}
        </main>
      </div>
    </div>
  );
}

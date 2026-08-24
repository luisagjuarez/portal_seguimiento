import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import InicioPage from "./components/InicioPage.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import SolicitudesPage from "./components/SolicitudesPage.jsx";
import SolicitudDetallePage from "./components/SolicitudDetallePage.jsx";
import TareaDetallePage from "./components/TareaDetallePage.jsx";
import TableroPage from "./components/TableroPage.jsx";
import UsuariosPage from "./components/UsuariosPage.jsx";
import LoginPage from "./components/LoginPage.jsx";
import { clearToken, fetchMe, getToken } from "./api.js";

const PAGINAS_QUE_REQUIEREN_SESION = new Set([
  "solicitudes",
  "solicitud-detalle",
  "tablero",
  "tarea-detalle",
  "usuarios",
]);

export default function App() {
  const [pagina, setPagina] = useState("inicio");
  const [solicitudSeleccionadaId, setSolicitudSeleccionadaId] = useState(null);
  const [tareaSeleccionadaId, setTareaSeleccionadaId] = useState(null);
  const [origenTarea, setOrigenTarea] = useState("solicitud");
  const [usuarioActual, setUsuarioActual] = useState(null);
  const [restaurandoSesion, setRestaurandoSesion] = useState(Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) {
      setRestaurandoSesion(false);
      return;
    }
    fetchMe()
      .then(setUsuarioActual)
      .catch(() => clearToken())
      .finally(() => setRestaurandoSesion(false));
  }, []);

  useEffect(() => {
    const alExpirarSesion = () => setUsuarioActual(null);
    window.addEventListener("dovela:sesion-expirada", alExpirarSesion);
    return () => window.removeEventListener("dovela:sesion-expirada", alExpirarSesion);
  }, []);

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

  const cerrarSesion = () => {
    clearToken();
    setUsuarioActual(null);
    setPagina("inicio");
  };

  const esScrumMaster = usuarioActual?.codigo_rol_scrum === "SCRUM MASTER";
  const requiereSesion = PAGINAS_QUE_REQUIEREN_SESION.has(pagina) && !usuarioActual;

  return (
    <div className="app-layout">
      <Sidebar
        paginaActual={pagina}
        onCambiarPagina={setPagina}
        usuarioActual={usuarioActual}
        esScrumMaster={esScrumMaster}
        onCerrarSesion={cerrarSesion}
      />
      <div className="main-content">
        <header>
          <h1>Portal de Seguimiento DOVELA</h1>
        </header>
        <main>
          {restaurandoSesion && <p>Cargando...</p>}
          {!restaurandoSesion && requiereSesion && <LoginPage onIngreso={setUsuarioActual} />}
          {!restaurandoSesion && !requiereSesion && (
            <>
              {pagina === "inicio" && <InicioPage onIrA={setPagina} />}
              {pagina === "chat" && <ChatWindow />}
              {pagina === "solicitudes" && <SolicitudesPage onVerDetalle={verDetalleSolicitud} />}
              {pagina === "solicitud-detalle" && (
                <SolicitudDetallePage
                  solicitudId={solicitudSeleccionadaId}
                  onRegresar={regresarASolicitudes}
                  onVerTarea={verDetalleTareaDesdeSolicitud}
                  esScrumMaster={esScrumMaster}
                />
              )}
              {pagina === "tablero" && <TableroPage onVerTarea={verDetalleTareaDesdeTablero} />}
              {pagina === "tarea-detalle" && (
                <TareaDetallePage tareaId={tareaSeleccionadaId} onRegresar={regresarDeTareaDetalle} />
              )}
              {pagina === "usuarios" && esScrumMaster && <UsuariosPage />}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

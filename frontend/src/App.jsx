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
import ResetPasswordPage from "./components/ResetPasswordPage.jsx";
import CambiarPasswordFormulario from "./components/CambiarPasswordFormulario.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import { clearToken, fetchMe, getToken } from "./api.js";

const SIDEBAR_STORAGE_KEY = "dovela:sidebar-visible";

function leerPreferenciaSidebar() {
  try {
    const guardado = localStorage.getItem(SIDEBAR_STORAGE_KEY);
    return guardado === null ? true : guardado === "true";
  } catch {
    return true;
  }
}

export default function App() {
  const [pagina, setPagina] = useState("inicio");
  const [solicitudSeleccionadaId, setSolicitudSeleccionadaId] = useState(null);
  const [tareaSeleccionadaId, setTareaSeleccionadaId] = useState(null);
  const [origenTarea, setOrigenTarea] = useState("solicitud");
  const [usuarioActual, setUsuarioActual] = useState(null);
  const [restaurandoSesion, setRestaurandoSesion] = useState(Boolean(getToken()));
  const [resetToken, setResetToken] = useState(
    () => new URLSearchParams(window.location.search).get("reset_token"),
  );
  const [sidebarVisible, setSidebarVisible] = useState(leerPreferenciaSidebar);

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

  const limpiarResetToken = () => {
    window.history.replaceState({}, "", window.location.pathname);
    setResetToken(null);
  };

  const alCambiarPasswordObligatorio = () => {
    setUsuarioActual((actual) => ({ ...actual, debe_cambiar_password: false }));
  };

  const alCambiarPasswordAutoservicio = () => {
    setUsuarioActual((actual) => ({ ...actual, debe_cambiar_password: false }));
    setPagina("inicio");
  };

  const alternarSidebar = () => {
    setSidebarVisible((actual) => {
      const nuevo = !actual;
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(nuevo));
      } catch {
        // la preferencia simplemente no persiste (p. ej. modo privado)
      }
      return nuevo;
    });
  };

  const esScrumMaster = usuarioActual?.codigo_rol_scrum === "SCRUM MASTER";
  const requiereSesion = !usuarioActual;
  const debeCambiarPassword = Boolean(usuarioActual?.debe_cambiar_password);
  const pantallaSinSidebar = Boolean(resetToken) || restaurandoSesion || requiereSesion || debeCambiarPassword;
  const puedeMostrarSidebar = usuarioActual && !debeCambiarPassword;
  const pantallaCentrada = pantallaSinSidebar || pagina === "inicio" || pagina === "chat";

  return (
    <div className="app-layout">
      {puedeMostrarSidebar && sidebarVisible && (
        <Sidebar
          paginaActual={pagina}
          onCambiarPagina={setPagina}
          usuarioActual={usuarioActual}
          esScrumMaster={esScrumMaster}
          onCerrarSesion={cerrarSesion}
        />
      )}
      <div className="main-content">
        <header>
          <div className="sidebar-toggle-wrap">
            {puedeMostrarSidebar && (
              <button
                type="button"
                className="theme-toggle"
                onClick={alternarSidebar}
                aria-label={sidebarVisible ? "Ocultar menú lateral" : "Mostrar menú lateral"}
                title={sidebarVisible ? "Ocultar menú" : "Mostrar menú"}
              >
                ☰
              </button>
            )}
          </div>
          <div className="theme-toggle-wrap">
            {puedeMostrarSidebar && (
              <button type="button" className="secundario" onClick={() => setPagina("cambiar-password")}>
                Cambiar contraseña
              </button>
            )}
            <ThemeToggle />
          </div>
        </header>
        <main className={pantallaCentrada ? "pantalla-centrada" : ""}>
          {resetToken && <ResetPasswordPage token={resetToken} onListo={limpiarResetToken} />}
          {!resetToken && restaurandoSesion && <p>Cargando...</p>}
          {!resetToken && !restaurandoSesion && requiereSesion && <LoginPage onIngreso={setUsuarioActual} />}
          {!resetToken && !restaurandoSesion && !requiereSesion && debeCambiarPassword && (
            <CambiarPasswordFormulario obligatorio onCambiada={alCambiarPasswordObligatorio} />
          )}
          {!resetToken && !restaurandoSesion && !requiereSesion && !debeCambiarPassword && (
            <>
              {pagina === "inicio" && <InicioPage usuarioActual={usuarioActual} onIrA={setPagina} />}
              {pagina === "chat" && <ChatWindow usuarioActual={usuarioActual} />}
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
                <TareaDetallePage
                  tareaId={tareaSeleccionadaId}
                  onRegresar={regresarDeTareaDetalle}
                  onVerSolicitud={verDetalleSolicitud}
                />
              )}
              {pagina === "usuarios" && esScrumMaster && <UsuariosPage />}
              {pagina === "cambiar-password" && (
                <CambiarPasswordFormulario
                  obligatorio={false}
                  onCambiada={alCambiarPasswordAutoservicio}
                  onCancelar={() => setPagina("inicio")}
                />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

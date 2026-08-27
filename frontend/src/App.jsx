import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import InicioPage from "./components/InicioPage.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import SolicitudesPage from "./components/SolicitudesPage.jsx";
import SolicitudDetallePage from "./components/SolicitudDetallePage.jsx";
import TareaDetallePage from "./components/TareaDetallePage.jsx";
import TableroPage from "./components/TableroPage.jsx";
import UsuariosPage from "./components/UsuariosPage.jsx";
import MonitorPage from "./components/MonitorPage.jsx";
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
  const navigate = useNavigate();
  const location = useLocation();
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

  const cerrarSesion = () => {
    clearToken();
    setUsuarioActual(null);
    navigate("/");
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
    navigate("/");
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
  const puedeVerMonitor = ["SCRUM MASTER", "PRODUCT OWNER"].includes(usuarioActual?.codigo_rol_scrum);
  const requiereSesion = !usuarioActual;
  const debeCambiarPassword = Boolean(usuarioActual?.debe_cambiar_password);
  const pantallaSinSidebar = Boolean(resetToken) || restaurandoSesion || requiereSesion || debeCambiarPassword;
  const puedeMostrarSidebar = usuarioActual && !debeCambiarPassword;
  const pantallaCentrada = pantallaSinSidebar || location.pathname === "/" || location.pathname === "/chat";

  return (
    <div className="app-layout">
      {puedeMostrarSidebar && sidebarVisible && (
        <Sidebar
          usuarioActual={usuarioActual}
          esScrumMaster={esScrumMaster}
          puedeVerMonitor={puedeVerMonitor}
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
              <button type="button" className="secundario" onClick={() => navigate("/cambiar-password")}>
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
            <Routes>
              <Route path="/" element={<InicioPage usuarioActual={usuarioActual} />} />
              <Route path="/chat" element={<ChatWindow usuarioActual={usuarioActual} />} />
              <Route path="/solicitudes" element={<SolicitudesPage />} />
              <Route
                path="/solicitudes/:id"
                element={<SolicitudDetallePage esScrumMaster={esScrumMaster} />}
              />
              <Route path="/tablero" element={<TableroPage />} />
              <Route
                path="/monitor"
                element={puedeVerMonitor ? <MonitorPage /> : <Navigate to="/" replace />}
              />
              <Route
                path="/tareas/:id"
                element={<TareaDetallePage usuarioActual={usuarioActual} esScrumMaster={esScrumMaster} />}
              />
              <Route
                path="/usuarios"
                element={esScrumMaster ? <UsuariosPage /> : <Navigate to="/" replace />}
              />
              <Route
                path="/cambiar-password"
                element={
                  <CambiarPasswordFormulario
                    obligatorio={false}
                    onCambiada={alCambiarPasswordAutoservicio}
                    onCancelar={() => navigate("/")}
                  />
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          )}
        </main>
      </div>
    </div>
  );
}

import { useState } from "react";
import { login, setToken } from "../api.js";
import RecuperarPasswordPage from "./RecuperarPasswordPage.jsx";

export default function LoginPage({ onIngreso }) {
  const [vista, setVista] = useState("login");
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  if (vista === "recuperar") {
    return <RecuperarPasswordPage onVolverALogin={() => setVista("login")} />;
  }

  const enviar = async (event) => {
    event.preventDefault();
    if (!usuario.trim() || !password) {
      setError("Ingresa tu usuario y contraseña.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const respuesta = await login(usuario.trim(), password);
      setToken(respuesta.access_token);
      onIngreso(respuesta.usuario_actual);
    } catch (err) {
      setError(err.message || "No se pudo iniciar sesión. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="inicio-page">
      <h2>Iniciar sesión</h2>
      <p>Esta sección es solo para el equipo DOVELA.</p>
      <form className="crear-solicitud-form" onSubmit={enviar}>
        <label>
          Usuario
          <input
            type="text"
            value={usuario}
            onChange={(event) => setUsuario(event.target.value)}
            placeholder="DOVELA_XX"
            autoComplete="username"
            required
          />
        </label>

        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {error && <p className="error-text">{error}</p>}

        <div className="resumen-acciones">
          <button type="submit" disabled={enviando}>
            {enviando ? "Entrando..." : "Entrar"}
          </button>
          <button type="button" className="enlace" onClick={() => setVista("recuperar")}>
            ¿Olvidaste tu contraseña?
          </button>
        </div>
      </form>
    </div>
  );
}

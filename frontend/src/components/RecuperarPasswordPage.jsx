import { useState } from "react";
import { forgotPassword } from "../api.js";

export default function RecuperarPasswordPage({ onVolverALogin }) {
  const [correo, setCorreo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [enviado, setEnviado] = useState(false);

  const enviar = async (event) => {
    event.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await forgotPassword(correo.trim());
      setEnviado(true);
    } catch (err) {
      setError(err.message || "No se pudo procesar la solicitud. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="inicio-page">
      <h2>Recuperar contraseña</h2>

      {enviado ? (
        <>
          <p>Si el correo está registrado, se envió un enlace de recuperación.</p>
          <div className="resumen-acciones">
            <button type="button" onClick={onVolverALogin}>
              Volver a iniciar sesión
            </button>
          </div>
        </>
      ) : (
        <form className="crear-solicitud-form" onSubmit={enviar}>
          <label>
            Correo electrónico
            <input
              type="email"
              value={correo}
              onChange={(event) => setCorreo(event.target.value)}
              placeholder="tu.correo@dovela.com"
              required
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <div className="resumen-acciones">
            <button type="submit" disabled={enviando}>
              {enviando ? "Enviando..." : "Enviar enlace de recuperación"}
            </button>
            <button type="button" className="secundario" disabled={enviando} onClick={onVolverALogin}>
              Volver a iniciar sesión
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

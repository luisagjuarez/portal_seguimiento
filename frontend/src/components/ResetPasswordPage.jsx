import { useState } from "react";
import { resetPassword } from "../api.js";

export default function ResetPasswordPage({ token, onListo }) {
  const [passwordNueva, setPasswordNueva] = useState("");
  const [passwordConfirmar, setPasswordConfirmar] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [listo, setListo] = useState(false);

  const enviar = async (event) => {
    event.preventDefault();
    if (passwordNueva.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (passwordNueva !== passwordConfirmar) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      await resetPassword(token, passwordNueva);
      setListo(true);
    } catch (err) {
      setError(err.message || "No se pudo restablecer la contraseña. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="inicio-page">
      <h2>Restablecer contraseña</h2>

      {listo ? (
        <>
          <p>Tu contraseña se actualizó correctamente.</p>
          <div className="resumen-acciones">
            <button type="button" onClick={onListo}>
              Ir a iniciar sesión
            </button>
          </div>
        </>
      ) : (
        <form className="crear-solicitud-form" onSubmit={enviar}>
          <label>
            Nueva contraseña
            <input
              type="password"
              value={passwordNueva}
              onChange={(event) => setPasswordNueva(event.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          <label>
            Confirmar nueva contraseña
            <input
              type="password"
              value={passwordConfirmar}
              onChange={(event) => setPasswordConfirmar(event.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <div className="resumen-acciones">
            <button type="submit" disabled={enviando}>
              {enviando ? "Guardando..." : "Restablecer contraseña"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

import { useState } from "react";
import { changePassword } from "../api.js";

export default function CambiarPasswordFormulario({ obligatorio, onCambiada, onCancelar }) {
  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");
  const [passwordConfirmar, setPasswordConfirmar] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (event) => {
    event.preventDefault();
    if (passwordNueva.length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (passwordNueva !== passwordConfirmar) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      await changePassword(passwordActual, passwordNueva);
      onCambiada();
    } catch (err) {
      setError(err.message || "No se pudo cambiar la contraseña. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="inicio-page">
      <h2>Cambiar contraseña</h2>
      {obligatorio && <p>Debes cambiar tu contraseña antes de continuar.</p>}

      <form className="crear-solicitud-form" onSubmit={enviar}>
        <label>
          Contraseña actual
          <input
            type="password"
            value={passwordActual}
            onChange={(event) => setPasswordActual(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

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
            {enviando ? "Guardando..." : "Cambiar contraseña"}
          </button>
          {!obligatorio && (
            <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
              Cancelar
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

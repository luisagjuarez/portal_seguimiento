import { useState } from "react";
import { otorgarAcceso } from "../api.js";

export default function AccesoFormulario({ miembro, roles, onGuardado, onCancelar }) {
  const [codigoRolScrum, setCodigoRolScrum] = useState(roles[0]?.codigo || "");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (event) => {
    event.preventDefault();
    if (!password || password.length < 8) {
      setError("La contraseña inicial debe tener al menos 8 caracteres.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const actualizado = await otorgarAcceso(miembro.id, { password, codigoRolScrum });
      onGuardado(actualizado);
    } catch (err) {
      setError(err.message || "No se pudo otorgar el acceso. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <p className="crear-solicitud-etiqueta">{miembro.nombre_completo} ({miembro.usuario})</p>

      <label>
        Rol Scrum
        <select value={codigoRolScrum} onChange={(event) => setCodigoRolScrum(event.target.value)} required>
          {roles.map((rol) => (
            <option key={rol.codigo} value={rol.codigo}>
              {rol.descripcion}
            </option>
          ))}
        </select>
      </label>

      <label>
        Contraseña inicial
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
      </label>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : "Otorgar acceso"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

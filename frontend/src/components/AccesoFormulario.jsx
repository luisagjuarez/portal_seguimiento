import { useState } from "react";
import { actualizarAcceso, otorgarAcceso } from "../api.js";

export default function AccesoFormulario({ miembro, roles, onGuardado, onCancelar }) {
  const esEdicion = miembro.acceso_activo;

  const [codigoRolScrum, setCodigoRolScrum] = useState(miembro.codigo_rol_scrum || roles[0]?.codigo || "");
  const [accesoActivo, setAccesoActivo] = useState(miembro.acceso_activo);
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (event) => {
    event.preventDefault();
    if (!esEdicion && (!password || password.length < 8)) {
      setError("La contraseña inicial debe tener al menos 8 caracteres.");
      return;
    }
    if (password && password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const actualizado = esEdicion
        ? await actualizarAcceso(miembro.id, { codigoRolScrum, accesoActivo, password: password || null })
        : await otorgarAcceso(miembro.id, { password, codigoRolScrum });
      onGuardado(actualizado);
    } catch (err) {
      setError(err.message || "No se pudo guardar el acceso. Intenta de nuevo.");
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

      {esEdicion && (
        <label>
          Acceso
          <select value={accesoActivo ? "activo" : "inactivo"} onChange={(event) => setAccesoActivo(event.target.value === "activo")}>
            <option value="activo">Activo</option>
            <option value="inactivo">Desactivado</option>
          </select>
        </label>
      )}

      <label>
        {esEdicion ? "Nueva contraseña (opcional)" : "Contraseña inicial"}
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder={esEdicion ? "Dejar vacío para no cambiarla" : ""}
          required={!esEdicion}
        />
      </label>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Otorgar acceso"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

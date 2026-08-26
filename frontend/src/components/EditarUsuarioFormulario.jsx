import { useState } from "react";
import { actualizarUsuario } from "../api.js";

export default function EditarUsuarioFormulario({ miembro, roles, onGuardado, onCancelar }) {
  const [usuario, setUsuario] = useState(miembro.usuario);
  const [nombreCompleto, setNombreCompleto] = useState(miembro.nombre_completo);
  const [correoElectronico, setCorreoElectronico] = useState(miembro.correo_electronico || "");
  const [codigoRolScrum, setCodigoRolScrum] = useState(miembro.codigo_rol_scrum || roles[0]?.codigo || "");
  const [accesoActivo, setAccesoActivo] = useState(miembro.acceso_activo);
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (event) => {
    event.preventDefault();
    if (!usuario.trim() || !nombreCompleto.trim()) {
      setError("Usuario y nombre completo no pueden quedar vacíos.");
      return;
    }
    if (password && password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const actualizado = await actualizarUsuario(miembro.id, {
        usuario: usuario.trim(),
        nombreCompleto: nombreCompleto.trim(),
        correoElectronico: correoElectronico.trim() || null,
        codigoRolScrum,
        accesoActivo,
        password: password || null,
      });
      onGuardado(actualizado);
    } catch (err) {
      setError(err.message || "No se pudo guardar el usuario. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="crear-solicitud-form" onSubmit={enviar}>
      <label>
        Usuario
        <input
          type="text"
          value={usuario}
          maxLength={255}
          onChange={(event) => setUsuario(event.target.value)}
          required
        />
      </label>

      <label>
        Nombre completo
        <input
          type="text"
          value={nombreCompleto}
          maxLength={255}
          onChange={(event) => setNombreCompleto(event.target.value)}
          required
        />
      </label>

      <label>
        Correo electrónico (opcional)
        <input
          type="email"
          value={correoElectronico}
          maxLength={255}
          onChange={(event) => setCorreoElectronico(event.target.value)}
        />
      </label>

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
        Acceso
        <select value={accesoActivo ? "activo" : "inactivo"} onChange={(event) => setAccesoActivo(event.target.value === "activo")}>
          <option value="activo">Activo</option>
          <option value="inactivo">Desactivado</option>
        </select>
      </label>

      <label>
        Nueva contraseña (opcional)
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Dejar vacío para no cambiarla"
        />
      </label>

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Guardando..." : "Guardar cambios"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

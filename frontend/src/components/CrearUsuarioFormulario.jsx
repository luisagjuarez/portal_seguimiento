import { useState } from "react";
import { crearUsuario } from "../api.js";

export default function CrearUsuarioFormulario({ onCreado, onCancelar }) {
  const [usuario, setUsuario] = useState("");
  const [nombreCompleto, setNombreCompleto] = useState("");
  const [correoElectronico, setCorreoElectronico] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (event) => {
    event.preventDefault();
    if (!usuario.trim() || !nombreCompleto.trim()) {
      setError("Completa usuario y nombre completo antes de crear el miembro.");
      return;
    }

    setEnviando(true);
    setError(null);
    try {
      const creado = await crearUsuario({
        usuario: usuario.trim(),
        nombreCompleto: nombreCompleto.trim(),
        correoElectronico: correoElectronico.trim() || null,
      });
      onCreado(creado);
    } catch (err) {
      setError(err.message || "No se pudo crear el usuario. Intenta de nuevo.");
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

      {error && <p className="error-text">{error}</p>}

      <div className="resumen-acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? "Creando..." : "Crear usuario"}
        </button>
        <button type="button" className="secundario" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

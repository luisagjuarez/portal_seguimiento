import { useEffect, useState } from "react";
import AccesoFormulario from "./AccesoFormulario.jsx";
import { fetchRolesScrum, fetchUsuarios } from "../api.js";

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [miembroEnEdicion, setMiembroEnEdicion] = useState(null);

  const cargar = () => {
    setCargando(true);
    setError(null);
    Promise.all([fetchUsuarios(), fetchRolesScrum()])
      .then(([listaUsuarios, listaRoles]) => {
        setUsuarios(listaUsuarios);
        setRoles(listaRoles);
      })
      .catch((err) => setError(err.message || "No se pudo cargar la lista de usuarios."))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargar();
  }, []);

  const alGuardarAcceso = () => {
    setMiembroEnEdicion(null);
    cargar();
  };

  if (cargando) {
    return <p>Cargando usuarios...</p>;
  }

  return (
    <div className="solicitudes-page">
      <div className="solicitudes-encabezado">
        <h2>Usuarios</h2>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="solicitud-detalle-info">
        <table className="tabla-usuarios">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Usuario</th>
              <th>Rol Scrum</th>
              <th>Acceso</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((usuario) => (
              <tr key={usuario.id}>
                <td>{usuario.nombre_completo}</td>
                <td>{usuario.usuario}</td>
                <td>{usuario.rol_scrum_descripcion || "Sin asignar"}</td>
                <td>
                  <span className={usuario.acceso_activo ? "tarea-estado tarea-estado-completa" : "tarea-estado"}>
                    {usuario.acceso_activo ? "Activo" : "Sin acceso"}
                  </span>
                </td>
                <td>
                  <button type="button" className="secundario" onClick={() => setMiembroEnEdicion(usuario)}>
                    {usuario.acceso_activo ? "Editar acceso" : "Otorgar acceso"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {miembroEnEdicion && (
        <div className="modal-overlay" onClick={() => setMiembroEnEdicion(null)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>{miembroEnEdicion.acceso_activo ? "Editar acceso" : "Otorgar acceso"}</h3>
            <AccesoFormulario
              miembro={miembroEnEdicion}
              roles={roles}
              onGuardado={alGuardarAcceso}
              onCancelar={() => setMiembroEnEdicion(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

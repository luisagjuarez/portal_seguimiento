import { useEffect, useState } from "react";
import AccesoFormulario from "./AccesoFormulario.jsx";
import EditarUsuarioFormulario from "./EditarUsuarioFormulario.jsx";
import CrearUsuarioFormulario from "./CrearUsuarioFormulario.jsx";
import ConfirmModal from "./ConfirmModal.jsx";
import { darDeBajaUsuario, fetchRolesScrum, fetchUsuarios } from "../api.js";

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [mostrarCrear, setMostrarCrear] = useState(false);
  const [miembroEnEdicion, setMiembroEnEdicion] = useState(null);
  const [miembroABajar, setMiembroABajar] = useState(null);
  const [bajando, setBajando] = useState(false);

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

  const alCrearUsuario = () => {
    setMostrarCrear(false);
    cargar();
  };

  const alGuardarAcceso = () => {
    setMiembroEnEdicion(null);
    cargar();
  };

  const confirmarBaja = async () => {
    setBajando(true);
    try {
      await darDeBajaUsuario(miembroABajar.id);
      setMiembroABajar(null);
      cargar();
    } catch (err) {
      setError(err.message || "No se pudo dar de baja al usuario.");
    } finally {
      setBajando(false);
    }
  };

  if (cargando) {
    return <p>Cargando usuarios...</p>;
  }

  return (
    <div className="solicitudes-page">
      <div className="solicitudes-encabezado">
        <h2>Usuarios</h2>
        <button type="button" onClick={() => setMostrarCrear(true)}>
          Crear usuario
        </button>
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
                    {usuario.acceso_activo ? "Editar usuario" : "Otorgar acceso"}
                  </button>
                  <button type="button" className="peligro" onClick={() => setMiembroABajar(usuario)}>
                    Dar de baja
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {mostrarCrear && (
        <div className="modal-overlay" onClick={() => setMostrarCrear(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>Crear usuario</h3>
            <CrearUsuarioFormulario onCreado={alCrearUsuario} onCancelar={() => setMostrarCrear(false)} />
          </div>
        </div>
      )}

      {miembroEnEdicion && (
        <div className="modal-overlay" onClick={() => setMiembroEnEdicion(null)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>{miembroEnEdicion.acceso_activo ? "Editar usuario" : "Otorgar acceso"}</h3>
            {miembroEnEdicion.acceso_activo ? (
              <EditarUsuarioFormulario
                miembro={miembroEnEdicion}
                roles={roles}
                onGuardado={alGuardarAcceso}
                onCancelar={() => setMiembroEnEdicion(null)}
              />
            ) : (
              <AccesoFormulario
                miembro={miembroEnEdicion}
                roles={roles}
                onGuardado={alGuardarAcceso}
                onCancelar={() => setMiembroEnEdicion(null)}
              />
            )}
          </div>
        </div>
      )}

      {miembroABajar && (
        <ConfirmModal
          titulo="Dar de baja"
          mensaje={`¿Seguro que quieres dar de baja a ${miembroABajar.nombre_completo}? Dejará de aparecer en Usuarios y en los selectores de solicitante/responsable, y perderá el acceso al portal.`}
          confirmando={bajando}
          textoConfirmar="Sí, dar de baja"
          textoConfirmando="Procesando..."
          onConfirmar={confirmarBaja}
          onCancelar={() => setMiembroABajar(null)}
        />
      )}
    </div>
  );
}

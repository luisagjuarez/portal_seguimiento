import logoDovela from "../assets/logo-dovela.png";

const OPCIONES = [
  { id: "inicio", etiqueta: "Inicio" },
  { id: "chat", etiqueta: "Solicitud por Chat" },
  { id: "solicitudes", etiqueta: "Solicitudes" },
  { id: "tablero", etiqueta: "Tablero" },
];

export default function Sidebar({ paginaActual, onCambiarPagina, usuarioActual, esScrumMaster, onCerrarSesion }) {
  const opciones = esScrumMaster ? [...OPCIONES, { id: "usuarios", etiqueta: "Usuarios" }] : OPCIONES;

  return (
    <nav className="sidebar">
      <img src={logoDovela} alt="Dovela Software" className="sidebar-logo" />
      <ul>
        {opciones.map((opcion) => (
          <li key={opcion.id}>
            <button
              type="button"
              className={opcion.id === paginaActual ? "sidebar-activo" : ""}
              onClick={() => onCambiarPagina(opcion.id)}
            >
              {opcion.etiqueta}
            </button>
          </li>
        ))}
      </ul>

      {usuarioActual && (
        <div className="sidebar-usuario">
          <p className="sidebar-usuario-nombre">{usuarioActual.nombre_completo}</p>
          <p className="sidebar-usuario-rol">{usuarioActual.codigo_rol_scrum}</p>
          <button type="button" className="secundario" onClick={onCerrarSesion}>
            Cerrar sesión
          </button>
        </div>
      )}
    </nav>
  );
}

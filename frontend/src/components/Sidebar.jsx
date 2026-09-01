import { NavLink } from "react-router-dom";
import logoDovela from "../assets/logo-dovela.png";

const OPCIONES = [
  { ruta: "/", etiqueta: "Inicio" },
  { ruta: "/chat", etiqueta: "Solicitud por Chat" },
  { ruta: "/solicitudes", etiqueta: "Solicitudes" },
  { ruta: "/tablero", etiqueta: "Tablero" },
];

export default function Sidebar({ usuarioActual, esScrumMaster, puedeVerReportesGerenciales, onCerrarSesion }) {
  let opciones = esScrumMaster ? [...OPCIONES, { ruta: "/usuarios", etiqueta: "Usuarios" }] : OPCIONES;
  if (puedeVerReportesGerenciales) {
    opciones = [
      ...opciones,
      { ruta: "/monitor", etiqueta: "Monitor" },
      { ruta: "/direccion-general", etiqueta: "Dirección General" },
    ];
  }

  return (
    <nav className="sidebar">
      <img src={logoDovela} alt="Dovela Software" className="sidebar-logo" />
      <ul>
        {opciones.map((opcion) => (
          <li key={opcion.ruta}>
            <NavLink
              to={opcion.ruta}
              end={opcion.ruta === "/"}
              className={({ isActive }) => (isActive ? "sidebar-activo" : "")}
            >
              {opcion.etiqueta}
            </NavLink>
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

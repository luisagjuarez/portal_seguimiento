const OPCIONES = [
  { id: "inicio", etiqueta: "Inicio" },
  { id: "chat", etiqueta: "Solicitud por Chat" },
  { id: "solicitudes", etiqueta: "Solicitudes" },
  { id: "tablero", etiqueta: "Tablero" },
];

export default function Sidebar({ paginaActual, onCambiarPagina }) {
  return (
    <nav className="sidebar">
      <p className="sidebar-titulo">DOVELA</p>
      <ul>
        {OPCIONES.map((opcion) => (
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
    </nav>
  );
}

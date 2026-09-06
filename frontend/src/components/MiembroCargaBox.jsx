import { useNavigate } from "react-router-dom";

export default function MiembroCargaBox({ miembro }) {
  const navigate = useNavigate();

  return (
    <div
      className="solicitud-card solicitud-card-clicable miembro-carga-box"
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/tablero?responsable=${miembro.id}`)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          navigate(`/tablero?responsable=${miembro.id}`);
        }
      }}
    >
      <span className="miembro-carga-box-icono" aria-hidden="true">
        🧑‍💻
      </span>
      <div className="miembro-carga-box-datos">
        <span className="miembro-carga-box-usuario">{miembro.usuario}</span>
        <span className="miembro-carga-box-nombre">{miembro.nombre_completo}</span>
      </div>
    </div>
  );
}

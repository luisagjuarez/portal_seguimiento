import { useDroppable } from "@dnd-kit/core";
import TareaCardTablero from "./TareaCardTablero.jsx";

export default function TableroColumna({ estatus, tareas, onAbrirTarea }) {
  const { setNodeRef, isOver } = useDroppable({ id: estatus.codigo });

  return (
    <div className={isOver ? "tablero-columna tablero-columna-activa" : "tablero-columna"}>
      <div className="tablero-columna-encabezado">
        <h3>{estatus.descripcion}</h3>
        <span className="tablero-columna-contador">{tareas.length}</span>
      </div>
      <div ref={setNodeRef} className="tablero-columna-lista">
        {tareas.map((tarea) => (
          <TareaCardTablero key={tarea.id} tarea={tarea} onAbrir={onAbrirTarea} />
        ))}
      </div>
    </div>
  );
}

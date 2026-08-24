import { useDraggable } from "@dnd-kit/core";

export default function TareaCardTablero({ tarea, onAbrir }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: tarea.id,
  });

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={isDragging ? "tarea-card-tablero tarea-card-tablero-arrastrando" : "tarea-card-tablero"}
      onClick={() => onAbrir(tarea.id)}
      {...listeners}
      {...attributes}
    >
      <h4>{tarea.nombre}</h4>
      <p className="tarea-card-tablero-referencia">
        {tarea.solicitud_nombre}
        {tarea.cliente ? ` · ${tarea.cliente}` : ""}
      </p>
      <p className="tarea-item-meta">
        <span>{tarea.responsable || "Sin asignar"}</span>
        <span className="solicitud-fecha">Vence: {tarea.fecha_fin}</span>
      </p>
    </div>
  );
}

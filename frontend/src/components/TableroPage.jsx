import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DndContext, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import TableroColumna from "./TableroColumna.jsx";
import { actualizarTarea, fetchEstatusTarea, fetchMiembrosEquipo, fetchTareasTablero } from "../api.js";

export default function TableroPage() {
  const navigate = useNavigate();
  const [tareas, setTareas] = useState([]);
  const [estatusTarea, setEstatusTarea] = useState([]);
  const [miembros, setMiembros] = useState([]);
  const [filtroCliente, setFiltroCliente] = useState("");
  const [filtroResponsable, setFiltroResponsable] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const cargarTareas = () => {
    setCargando(true);
    setError(null);
    fetchTareasTablero({ cliente: filtroCliente, responsableId: filtroResponsable || undefined })
      .then(setTareas)
      .catch((err) => setError(err.message || "No se pudieron cargar las tareas."))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    fetchEstatusTarea()
      .then(setEstatusTarea)
      .catch(() => setError("No se pudo cargar el catálogo de estatus de tarea."));
    fetchMiembrosEquipo()
      .then(setMiembros)
      .catch(() => {
        /* el filtro de responsable queda solo con "Todos" si esto falla */
      });
  }, []);

  useEffect(() => {
    const timeoutId = setTimeout(cargarTareas, 300);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroCliente, filtroResponsable]);

  const alTerminarDrag = async (event) => {
    const { active, over } = event;
    if (!over) return;

    const tareaId = active.id;
    const nuevoEstatus = over.id;
    const tarea = tareas.find((t) => t.id === tareaId);
    if (!tarea || tarea.codigo_estatus_tarea === nuevoEstatus) return;

    const tareasAnteriores = tareas;
    setTareas((actuales) =>
      actuales.map((t) => (t.id === tareaId ? { ...t, codigo_estatus_tarea: nuevoEstatus } : t)),
    );

    try {
      await actualizarTarea(tareaId, {
        nombre: tarea.nombre,
        descripcion: tarea.descripcion,
        responsableId: tarea.responsable_id,
        codigoEstatusTarea: nuevoEstatus,
        fechaInicio: tarea.fecha_inicio,
        fechaFin: tarea.fecha_fin,
        horasEstimadas: tarea.horas_estimadas,
        horasReales: tarea.horas_reales,
      });
    } catch (err) {
      setTareas(tareasAnteriores);
      setError(err.message || "No se pudo actualizar el estatus de la tarea.");
    }
  };

  return (
    <div className="tablero-page">
      <div className="solicitudes-encabezado">
        <h2>Tablero</h2>
      </div>

      <div className="solicitudes-filtros">
        <input
          type="text"
          placeholder="Filtrar por cliente..."
          value={filtroCliente}
          onChange={(event) => setFiltroCliente(event.target.value)}
        />
        <select value={filtroResponsable} onChange={(event) => setFiltroResponsable(event.target.value)}>
          <option value="">Todos los responsables</option>
          {miembros.map((miembro) => (
            <option key={miembro.id} value={miembro.id}>
              {miembro.nombre_completo}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="error-text">{error}</p>}
      {cargando && <p>Cargando tablero...</p>}

      {!cargando && (
        <DndContext sensors={sensors} onDragEnd={alTerminarDrag}>
          <div className="tablero-columnas">
            {estatusTarea.map((estatus) => (
              <TableroColumna
                key={estatus.codigo}
                estatus={estatus}
                tareas={tareas.filter((t) => t.codigo_estatus_tarea === estatus.codigo)}
                onAbrirTarea={(id) => navigate(`/tareas/${id}`)}
              />
            ))}
          </div>
        </DndContext>
      )}
    </div>
  );
}

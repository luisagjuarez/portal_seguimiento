import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { DndContext, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import TableroColumna from "./TableroColumna.jsx";
import FiltroResponsableMultiple from "./FiltroResponsableMultiple.jsx";
import { actualizarTarea, fetchEstatusTarea, fetchMiembrosEquipo, fetchTareasTablero } from "../api.js";

const ROLES_VEN_TODAS_POR_DEFAULT = new Set(["PRODUCT OWNER"]);
const DIAS_VENTANA_DEFAULT = 8;

function hoyISO() {
  return new Date().toISOString().slice(0, 10);
}

function haceDiasISO(dias) {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - dias);
  return fecha.toISOString().slice(0, 10);
}

export default function TableroPage({ usuarioActual }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tareas, setTareas] = useState([]);
  const [estatusTarea, setEstatusTarea] = useState([]);
  const [miembros, setMiembros] = useState([]);
  const [filtroCliente, setFiltroCliente] = useState("");
  // Por defecto, cada quien ve solo sus propias tareas; solo Product Owner ve todas por
  // default (necesita la vista completa del equipo) — Scrum Master también arranca en las
  // suyas. "Todos los responsables" sigue disponible para cualquiera que quiera cambiarlo
  // manualmente (ahora multi-selectivo, agrupado por área). Si se llega con ?responsable=<id>
  // en la URL (deep link desde "Carga del equipo"), ese valor manda sobre el default de rol.
  const [filtroResponsables, setFiltroResponsables] = useState(() => {
    const responsableUrl = searchParams.get("responsable");
    if (responsableUrl) return [responsableUrl];
    return usuarioActual && !ROLES_VEN_TODAS_POR_DEFAULT.has(usuarioActual.codigo_rol_scrum)
      ? [String(usuarioActual.id)]
      : [];
  });
  // Punto 1 (2026-09-07): delimita la fecha de término (fecha_fin) planeada de las tareas.
  // Por defecto, los últimos 8 días hasta hoy.
  const [desde, setDesde] = useState(() => haceDiasISO(DIAS_VENTANA_DEFAULT));
  const [hasta, setHasta] = useState(hoyISO);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const cargarTareas = () => {
    setCargando(true);
    setError(null);
    fetchTareasTablero({ cliente: filtroCliente, responsableIds: filtroResponsables, desde, hasta })
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
  }, [filtroCliente, filtroResponsables, desde, hasta]);

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
        <h2>Tablero de tareas</h2>
      </div>

      <div className="solicitudes-filtros">
        <input
          type="text"
          placeholder="Filtrar por cliente..."
          value={filtroCliente}
          onChange={(event) => setFiltroCliente(event.target.value)}
        />
        <div className="direccion-general-rango">
          <label>
            Fecha inicio
            <input type="date" value={desde} max={hasta} onChange={(e) => setDesde(e.target.value)} />
          </label>
          <label>
            Fecha fin
            <input type="date" value={hasta} min={desde} onChange={(e) => setHasta(e.target.value)} />
          </label>
        </div>
        <FiltroResponsableMultiple miembros={miembros} valor={filtroResponsables} onCambiar={setFiltroResponsables} />
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

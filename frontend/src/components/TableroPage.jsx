import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { DndContext, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import TableroColumna from "./TableroColumna.jsx";
import FiltroMultiple from "./FiltroMultiple.jsx";
import {
  actualizarTarea,
  fetchClientes,
  fetchEstatusTarea,
  fetchMiembrosEquipo,
  fetchPerfilesEquipo,
  fetchTareasTablero,
} from "../api.js";

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
  const [areas, setAreas] = useState([]);
  const [clientesCatalogo, setClientesCatalogo] = useState([]);
  const [filtroClientes, setFiltroClientes] = useState([]);
  const [area, setArea] = useState("");
  // Por defecto, cada quien ve solo sus propias tareas; solo Product Owner ve todas por
  // default (necesita la vista completa del equipo) — Scrum Master también arranca en las
  // suyas. "Todos los responsables" sigue disponible para cualquiera que quiera cambiarlo
  // manualmente (multi-selectivo, acotado por el área seleccionada). Si se llega con
  // ?responsable=<id> en la URL (deep link desde "Carga del equipo"), ese valor manda sobre
  // el default de rol.
  const [filtroResponsables, setFiltroResponsables] = useState(() => {
    const responsableUrl = searchParams.get("responsable");
    if (responsableUrl) return [responsableUrl];
    return usuarioActual && !ROLES_VEN_TODAS_POR_DEFAULT.has(usuarioActual.codigo_rol_scrum)
      ? [String(usuarioActual.id)]
      : [];
  });
  // Puntos 1-2 (2026-09-07): delimitan fecha_fin_real y solo aplican a tareas Completadas —
  // el resto se muestra siempre. Por defecto, los últimos 8 días hasta hoy.
  const [desde, setDesde] = useState(() => haceDiasISO(DIAS_VENTANA_DEFAULT));
  const [hasta, setHasta] = useState(hoyISO);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  // Punto 4: el filtro de Responsable queda acotado por el Área seleccionada (Punto 3).
  const miembrosFiltrados = area ? miembros.filter((m) => (m.perfil || "Sin área") === area) : miembros;

  const cargarTareas = () => {
    setCargando(true);
    setError(null);
    fetchTareasTablero({ clientes: filtroClientes, responsableIds: filtroResponsables, area, desde, hasta })
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
    fetchPerfilesEquipo()
      .then(setAreas)
      .catch(() => setAreas([]));
    fetchClientes()
      .then(setClientesCatalogo)
      .catch(() => setClientesCatalogo([]));
  }, []);

  // Si cambia el área, se quitan de la selección los responsables que ya no pertenecen a ella.
  useEffect(() => {
    setFiltroResponsables((actuales) => {
      const idsVisibles = new Set(miembrosFiltrados.map((m) => String(m.id)));
      const filtrados = actuales.filter((id) => idsVisibles.has(id));
      return filtrados.length === actuales.length ? actuales : filtrados;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area, miembros]);

  useEffect(() => {
    const timeoutId = setTimeout(cargarTareas, 300);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroClientes, filtroResponsables, area, desde, hasta]);

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
        <select value={area} onChange={(e) => setArea(e.target.value)}>
          <option value="">Todas las áreas</option>
          {areas.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <FiltroMultiple
          etiqueta="Responsable"
          opciones={miembrosFiltrados.map((m) => ({ id: m.id, etiqueta: m.nombre_completo }))}
          valor={filtroResponsables}
          onCambiar={setFiltroResponsables}
        />
        <FiltroMultiple
          etiqueta="Cliente"
          opciones={clientesCatalogo.map((c) => ({ id: c, etiqueta: c }))}
          valor={filtroClientes}
          onCambiar={setFiltroClientes}
        />
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

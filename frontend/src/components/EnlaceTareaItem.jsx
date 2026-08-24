function formatearFecha(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function EnlaceTareaItem({ enlace, mostrarTarea }) {
  return (
    <div className="hito-card">
      <h4>{enlace.tipo_enlace}</h4>
      {enlace.url && (
        <p>
          <a href={enlace.url} target="_blank" rel="noopener noreferrer">
            {enlace.url}
          </a>
        </p>
      )}
      {(enlace.aplicacion_id || enlace.pagina_aplicacion) && (
        <p>
          Aplicación: {enlace.aplicacion_id ?? "—"} · Página: {enlace.pagina_aplicacion ?? "—"}
        </p>
      )}
      {enlace.descripcion && <p>{enlace.descripcion}</p>}
      {mostrarTarea && enlace.tarea_nombre && <p className="solicitud-fecha">Tarea: {enlace.tarea_nombre}</p>}
      <p className="solicitud-fecha">
        {enlace.creado_por_nombre} · {formatearFecha(enlace.creado_en)}
      </p>
    </div>
  );
}

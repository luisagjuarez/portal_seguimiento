// Semáforo de vencimiento (Fase 1.18): distinto del semáforo de prioridad (Fase 1.17).
// Reusa la misma ventana de 7 días que ya usa el Monitor para "por vencer"
// (repository.list_tareas_por_vencer, dias_ventana=7).
const DIAS_VENTANA_PROXIMA = 7;
const ESTATUS_SIN_URGENCIA = new Set(["COMPLETADO", "CANCELADO"]);

export function claseVencimiento(fechaEntrega, codigoEstatus, hoy = new Date()) {
  if (!fechaEntrega || ESTATUS_SIN_URGENCIA.has(codigoEstatus)) {
    return null;
  }
  const dias = Math.ceil((new Date(`${fechaEntrega}T00:00:00`) - hoy) / 86400000);
  if (dias < 0) {
    return { clase: "vencimiento-vencida", etiqueta: "Vencida" };
  }
  if (dias <= DIAS_VENTANA_PROXIMA) {
    return { clase: "vencimiento-proxima", etiqueta: "Vence pronto" };
  }
  return { clase: "vencimiento-normal", etiqueta: "En tiempo" };
}

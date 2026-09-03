// Semáforo de prioridad (Fase 1.17). Niveles y colores fijos según el estándar de la
// empresa (00_ARCHIVOS/matriz_prioridades_scrum.md), no un catálogo editable en BD.
export const PRIORIDAD_INFO = {
  1: { etiqueta: "Crítica", clase: "prioridad-1" },
  2: { etiqueta: "Alta", clase: "prioridad-2" },
  3: { etiqueta: "Media", clase: "prioridad-3" },
  4: { etiqueta: "Baja", clase: "prioridad-4" },
  5: { etiqueta: "Trivial", clase: "prioridad-5" },
};

export const NIVELES_PRIORIDAD = [1, 2, 3, 4, 5];

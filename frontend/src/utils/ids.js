export function formatearIdSolicitud(solicitudId) {
  return `S-${solicitudId}`;
}

export function formatearIdTarea(solicitudId, tareaId) {
  return `S-${solicitudId}-T-${tareaId}`;
}

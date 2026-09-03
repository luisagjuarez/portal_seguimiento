function resolveApiBaseUrl() {
  // En dev (npm run dev) no hay nginx haciendo de reverse proxy de la API: se usa la
  // variable de entorno de Vite, con un default razonable para desarrollo local.
  if (import.meta.env.DEV) {
    return import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  }
  // En producción (build servido por el nginx del contenedor frontend) la API siempre
  // vive en el mismo origen que la página, bajo /dovela_control/api — el nginx del
  // frontend la reverse-proxea internamente. Calcularlo desde window.location.origin (en
  // vez de grabar un origen fijo en el build) es lo único que funciona sin importar por
  // qué dominio/IP/protocolo se haya llegado (localhost, IP interna, o un dominio HTTPS
  // detrás de un reverse proxy de infraestructura) — un valor fijo nunca puede servir para
  // los tres a la vez, y mezclar http/https dispara bloqueos de "mixed content".
  return `${window.location.origin}/dovela_control`;
}

const API_BASE_URL = resolveApiBaseUrl();

const TOKEN_STORAGE_KEY = "dovela_token";

function leerTokenGuardado() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    // localStorage puede no estar disponible (modo privado, etc.)
    return null;
  }
}

let tokenActual = leerTokenGuardado();

export function getToken() {
  return tokenActual;
}

export function setToken(token) {
  tokenActual = token;
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // si no se puede persistir, la sesión solo dura mientras la pestaña esté abierta
  }
}

export function clearToken() {
  tokenActual = null;
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // nada que limpiar si nunca se pudo guardar
  }
}

function authHeaders() {
  return tokenActual ? { Authorization: `Bearer ${tokenActual}` } : {};
}

function extraerMensaje(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  // FastAPI manda los errores de validación (422) como una lista de objetos
  // {loc, msg, type}, no como texto plano.
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join(" — ");
  }
  return fallback;
}

async function lanzarSiError(response) {
  if (response.status === 401) {
    clearToken();
    window.dispatchEvent(new Event("dovela:sesion-expirada"));
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = extraerMensaje(body.detail, detail);
    } catch {
      // sin cuerpo JSON, se conserva el statusText
    }
    throw new Error(detail);
  }
}

async function parseJsonOrThrow(response) {
  await lanzarSiError(response);
  return response.json();
}

export async function login(usuario, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, password }),
  });
  return parseJsonOrThrow(response);
}

export async function fetchMe() {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function forgotPassword(correoElectronico) {
  const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ correo_electronico: correoElectronico }),
  });
  return parseJsonOrThrow(response);
}

export async function resetPassword(token, passwordNueva) {
  const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password_nueva: passwordNueva }),
  });
  return parseJsonOrThrow(response);
}

export async function changePassword(passwordActual, passwordNueva) {
  const response = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ password_actual: passwordActual, password_nueva: passwordNueva }),
  });
  return parseJsonOrThrow(response);
}

export async function fetchRolesScrum() {
  const response = await fetch(`${API_BASE_URL}/api/roles-scrum`);
  return parseJsonOrThrow(response);
}

export async function fetchUsuarios() {
  const response = await fetch(`${API_BASE_URL}/api/usuarios`, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function otorgarAcceso(miembroId, { password, codigoRolScrum }) {
  const response = await fetch(`${API_BASE_URL}/api/usuarios/${miembroId}/acceso`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ password, codigo_rol_scrum: codigoRolScrum }),
  });
  return parseJsonOrThrow(response);
}

export async function crearUsuario({ usuario, nombreCompleto, correoElectronico }) {
  const response = await fetch(`${API_BASE_URL}/api/usuarios`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      usuario,
      nombre_completo: nombreCompleto,
      correo_electronico: correoElectronico || null,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function actualizarUsuario(
  miembroId,
  { usuario, nombreCompleto, correoElectronico, codigoRolScrum, accesoActivo, password },
) {
  const response = await fetch(`${API_BASE_URL}/api/usuarios/${miembroId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      usuario: usuario || null,
      nombre_completo: nombreCompleto || null,
      correo_electronico: correoElectronico || null,
      codigo_rol_scrum: codigoRolScrum ?? null,
      acceso_activo: accesoActivo ?? null,
      password: password || null,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function darDeBajaUsuario(miembroId) {
  const response = await fetch(`${API_BASE_URL}/api/usuarios/${miembroId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function fetchClientes(query) {
  const url = new URL(`${API_BASE_URL}/api/clientes`);
  if (query) {
    url.searchParams.set("q", query);
  }
  const response = await fetch(url);
  const data = await parseJsonOrThrow(response);
  return data.map((item) => item.nombre);
}

export async function crearSolicitudChat({ solicitanteEmail, titulo, descripcion, cliente, adjuntos }) {
  const formData = new FormData();
  formData.append("solicitante_email", solicitanteEmail);
  formData.append("titulo", titulo);
  formData.append("descripcion", descripcion);
  if (cliente) {
    formData.append("cliente", cliente);
  }
  for (const archivo of adjuntos || []) {
    formData.append("files", archivo);
  }

  // Sin header Content-Type manual: el navegador arma el boundary correcto de multipart.
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/chat`, {
    method: "POST",
    body: formData,
  });
  return parseJsonOrThrow(response);
}

export async function fetchSolicitudes({ cliente, nombre, estatus, ordenPor, involucradoId } = {}) {
  const url = new URL(`${API_BASE_URL}/api/solicitudes`);
  if (cliente) url.searchParams.set("cliente", cliente);
  if (nombre) url.searchParams.set("nombre", nombre);
  if (estatus) url.searchParams.set("estatus", estatus);
  if (ordenPor) url.searchParams.set("orden_por", ordenPor);
  if (involucradoId) url.searchParams.set("involucrado_id", involucradoId);
  const response = await fetch(url, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function fetchTareasTablero({ cliente, responsableId } = {}) {
  const url = new URL(`${API_BASE_URL}/api/tareas`);
  if (cliente) url.searchParams.set("cliente", cliente);
  if (responsableId) url.searchParams.set("responsable_id", responsableId);
  const response = await fetch(url, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function fetchMiembrosEquipo() {
  const response = await fetch(`${API_BASE_URL}/api/miembros-equipo`);
  return parseJsonOrThrow(response);
}

export async function fetchInicioResumen() {
  const response = await fetch(`${API_BASE_URL}/api/inicio/resumen`, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function fetchMonitorKpis() {
  const response = await fetch(`${API_BASE_URL}/api/monitor/kpis`, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function fetchDireccionGeneralKpis(desde, hasta) {
  const url = new URL(`${API_BASE_URL}/api/direccion-general/kpis`);
  url.searchParams.set("desde", desde);
  url.searchParams.set("hasta", hasta);
  const response = await fetch(url, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function fetchDireccionGeneralDetalleSolicitudes(metrica, desde, hasta) {
  const url = new URL(`${API_BASE_URL}/api/direccion-general/detalle-solicitudes`);
  url.searchParams.set("metrica", metrica);
  url.searchParams.set("desde", desde);
  url.searchParams.set("hasta", hasta);
  const response = await fetch(url, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function fetchTiposSolicitud() {
  const response = await fetch(`${API_BASE_URL}/api/tipos-solicitud`);
  return parseJsonOrThrow(response);
}

export async function fetchEstatus() {
  const response = await fetch(`${API_BASE_URL}/api/estatus`);
  return parseJsonOrThrow(response);
}

export async function fetchCanalesSolicitud() {
  const response = await fetch(`${API_BASE_URL}/api/canales-solicitud`);
  return parseJsonOrThrow(response);
}

export async function fetchEstatusTarea() {
  const response = await fetch(`${API_BASE_URL}/api/estatus-tarea`);
  return parseJsonOrThrow(response);
}

export async function fetchSolicitudDetalle(id) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${id}`, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function actualizarSolicitud(
  id,
  {
    nombre,
    descripcion,
    cliente,
    tipo,
    canal,
    codigoEstatus,
    ordenPrioridad,
    fechaCompletado,
    fechaEntrega,
    responsableAtencionId,
  },
) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      nombre,
      descripcion,
      cliente,
      tipo,
      canal,
      codigo_estatus: codigoEstatus,
      orden_prioridad: ordenPrioridad,
      fecha_completado: fechaCompletado || null,
      fecha_entrega: fechaEntrega || null,
      responsable_atencion_id: responsableAtencionId || null,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function actualizarSolicitudExterna(id, { nombre, descripcion, cliente, tipo }) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${id}/mi-solicitud`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ nombre, descripcion, cliente, tipo }),
  });
  return parseJsonOrThrow(response);
}

export async function eliminarSolicitud(id) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function fetchTareas(solicitudId) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/tareas`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function crearTarea(
  solicitudId,
  {
    nombre,
    descripcion,
    responsableId,
    codigoEstatusTarea,
    fechaInicio,
    fechaFin,
    fechaInicioReal,
    fechaFinReal,
    horasEstimadas,
    horasReales,
  },
) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/tareas`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      nombre,
      descripcion,
      responsable_id: responsableId,
      codigo_estatus_tarea: codigoEstatusTarea,
      fecha_inicio: fechaInicio,
      fecha_fin: fechaFin,
      fecha_inicio_real: fechaInicioReal,
      fecha_fin_real: fechaFinReal,
      horas_estimadas: horasEstimadas,
      horas_reales: horasReales,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function actualizarTarea(
  tareaId,
  {
    nombre,
    descripcion,
    responsableId,
    codigoEstatusTarea,
    fechaInicio,
    fechaFin,
    fechaInicioReal,
    fechaFinReal,
    horasEstimadas,
    horasReales,
  },
) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      nombre,
      descripcion,
      responsable_id: responsableId,
      codigo_estatus_tarea: codigoEstatusTarea,
      fecha_inicio: fechaInicio,
      fecha_fin: fechaFin,
      fecha_inicio_real: fechaInicioReal,
      fecha_fin_real: fechaFinReal,
      horas_estimadas: horasEstimadas,
      horas_reales: horasReales,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function eliminarTarea(tareaId) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function fetchTareaDetalle(id) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${id}`, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function fetchHitoDeTarea(tareaId) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/hito`, { headers: authHeaders() });
  if (response.status === 404) {
    return null;
  }
  return parseJsonOrThrow(response);
}

function datosHito({ nombre, descripcion, fechaVencimiento }) {
  return { nombre, descripcion, fecha_vencimiento: fechaVencimiento };
}

export async function crearHitoTarea(tareaId, datos) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/hito`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(datosHito(datos)),
  });
  return parseJsonOrThrow(response);
}

export async function actualizarHitoTarea(tareaId, datos) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/hito`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(datosHito(datos)),
  });
  return parseJsonOrThrow(response);
}

export async function eliminarHitoTarea(tareaId) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/hito`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function fetchComentariosTarea(tareaId) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/comentarios`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function crearComentarioTarea(tareaId, texto) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/comentarios`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ texto_comentario: texto }),
  });
  return parseJsonOrThrow(response);
}

export async function crearComentarioSolicitud(solicitudId, texto) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/comentarios`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ texto_comentario: texto }),
  });
  return parseJsonOrThrow(response);
}

export async function actualizarComentario(comentarioId, texto) {
  const response = await fetch(`${API_BASE_URL}/api/comentarios/${comentarioId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ texto_comentario: texto }),
  });
  return parseJsonOrThrow(response);
}

export async function eliminarComentario(comentarioId) {
  const response = await fetch(`${API_BASE_URL}/api/comentarios/${comentarioId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function fetchPorHacerTarea(tareaId) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/por-hacer`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function crearPorHacer(tareaId, { nombre, descripcion, responsableId }) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/por-hacer`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      nombre,
      descripcion: descripcion || null,
      responsable_id: responsableId || null,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function actualizarPorHacer(itemId, { nombre, descripcion, responsableId, estaCompleta }) {
  const response = await fetch(`${API_BASE_URL}/api/tarea-por-hacer/${itemId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      nombre,
      descripcion: descripcion || null,
      responsable_id: responsableId || null,
      esta_completa: estaCompleta,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function eliminarPorHacer(itemId) {
  const response = await fetch(`${API_BASE_URL}/api/tarea-por-hacer/${itemId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function fetchEnlacesTarea(tareaId) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/enlaces`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function crearEnlaceTarea(tareaId, { tipoEnlace, url, aplicacionId, paginaAplicacion, descripcion }) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/enlaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      tipo_enlace: tipoEnlace,
      url: url || null,
      aplicacion_id: aplicacionId || null,
      pagina_aplicacion: paginaAplicacion || null,
      descripcion: descripcion || null,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function fetchComentariosSolicitud(solicitudId) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/comentarios`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function fetchHitosSolicitud(solicitudId) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/hitos`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function fetchEnlacesSolicitud(solicitudId) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/enlaces`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function fetchAdjuntosSolicitud(solicitudId) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/adjuntos`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function descargarAdjuntoSolicitud(solicitudId, adjuntoId, nombreArchivo) {
  const response = await fetch(
    `${API_BASE_URL}/api/solicitudes/${solicitudId}/adjuntos/${adjuntoId}/descargar`,
    { headers: authHeaders() },
  );
  await lanzarSiError(response);

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}

export async function crearSolicitudFormulario({
  solicitanteEmail,
  titulo,
  descripcion,
  tipo,
  canal,
  ordenPrioridad,
  cliente,
  adjuntos,
}) {
  const formData = new FormData();
  formData.append("solicitante_email", solicitanteEmail);
  formData.append("titulo", titulo);
  formData.append("descripcion", descripcion);
  formData.append("tipo", tipo);
  formData.append("canal", canal);
  formData.append("orden_prioridad", ordenPrioridad);
  if (cliente) {
    formData.append("cliente", cliente);
  }
  for (const archivo of adjuntos || []) {
    formData.append("files", archivo);
  }

  const response = await fetch(`${API_BASE_URL}/api/solicitudes/formulario`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  return parseJsonOrThrow(response);
}

export async function fetchNotificaciones({ soloNoLeidas } = {}) {
  const url = new URL(`${API_BASE_URL}/api/notificaciones`);
  if (soloNoLeidas) url.searchParams.set("solo_no_leidas", "true");
  const response = await fetch(url, { headers: authHeaders() });
  return parseJsonOrThrow(response);
}

export async function fetchNotificacionesNoLeidasCount() {
  const response = await fetch(`${API_BASE_URL}/api/notificaciones/no-leidas/count`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function marcarNotificacionLeida(id) {
  const response = await fetch(`${API_BASE_URL}/api/notificaciones/${id}/leer`, {
    method: "PUT",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function marcarTodasNotificacionesLeidas() {
  const response = await fetch(`${API_BASE_URL}/api/notificaciones/leer-todas`, {
    method: "PUT",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function agregarAdjuntosSolicitud(solicitudId, archivos) {
  const formData = new FormData();
  for (const archivo of archivos) {
    formData.append("files", archivo);
  }
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/adjuntos`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  return parseJsonOrThrow(response);
}

export async function fetchAdjuntosTarea(tareaId) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/adjuntos`, {
    headers: authHeaders(),
  });
  return parseJsonOrThrow(response);
}

export async function agregarAdjuntosTarea(tareaId, archivos) {
  const formData = new FormData();
  for (const archivo of archivos) {
    formData.append("files", archivo);
  }
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/adjuntos`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  return parseJsonOrThrow(response);
}

export async function descargarAdjuntoTarea(tareaId, adjuntoId, nombreArchivo) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}/adjuntos/${adjuntoId}/descargar`, {
    headers: authHeaders(),
  });
  await lanzarSiError(response);

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}

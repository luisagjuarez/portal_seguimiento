const PLACEHOLDER = "API_BASE_URL_PLACEHOLDER";

function resolveApiBaseUrl() {
  const runtimeValue = window.__API_BASE_URL__;
  if (runtimeValue && runtimeValue !== PLACEHOLDER) {
    return runtimeValue;
  }
  // Fuera de Docker (npm run dev/preview) config.js nunca se sustituye: se usa la
  // variable de entorno de Vite, con un default razonable para desarrollo local.
  return import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
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

async function parseJsonOrThrow(response) {
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

export async function actualizarAcceso(miembroId, { codigoRolScrum, accesoActivo, password }) {
  const response = await fetch(`${API_BASE_URL}/api/usuarios/${miembroId}/acceso`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      codigo_rol_scrum: codigoRolScrum ?? null,
      acceso_activo: accesoActivo ?? null,
      password: password || null,
    }),
  });
  return parseJsonOrThrow(response);
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

export async function fetchSolicitudes({ cliente, nombre, estatus, ordenPor } = {}) {
  const url = new URL(`${API_BASE_URL}/api/solicitudes`);
  if (cliente) url.searchParams.set("cliente", cliente);
  if (nombre) url.searchParams.set("nombre", nombre);
  if (estatus) url.searchParams.set("estatus", estatus);
  if (ordenPor) url.searchParams.set("orden_por", ordenPor);
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
  { nombre, descripcion, cliente, tipo, canal, codigoEstatus, ordenPrioridad, fechaCompletado },
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
      orden_prioridad: ordenPrioridad || null,
      fecha_completado: fechaCompletado || null,
    }),
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
  { nombre, descripcion, responsableId, codigoEstatusTarea, fechaInicio, fechaFin, horasEstimadas, horasReales },
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
      horas_estimadas: horasEstimadas,
      horas_reales: horasReales,
    }),
  });
  return parseJsonOrThrow(response);
}

export async function actualizarTarea(
  tareaId,
  { nombre, descripcion, responsableId, codigoEstatusTarea, fechaInicio, fechaFin, horasEstimadas, horasReales },
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
  if (ordenPrioridad) {
    formData.append("orden_prioridad", ordenPrioridad);
  }
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

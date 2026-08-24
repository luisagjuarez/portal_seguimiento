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

export async function fetchSolicitudes({ cliente, nombre, estatus } = {}) {
  const url = new URL(`${API_BASE_URL}/api/solicitudes`);
  if (cliente) url.searchParams.set("cliente", cliente);
  if (nombre) url.searchParams.set("nombre", nombre);
  if (estatus) url.searchParams.set("estatus", estatus);
  const response = await fetch(url);
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

export async function fetchSolicitudDetalle(id) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${id}`);
  return parseJsonOrThrow(response);
}

export async function actualizarSolicitud(id, { nombre, descripcion, cliente, tipo, codigoEstatus }) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre, descripcion, cliente, tipo, codigo_estatus: codigoEstatus }),
  });
  return parseJsonOrThrow(response);
}

export async function eliminarSolicitud(id) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${id}`, { method: "DELETE" });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function fetchTareas(solicitudId) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/tareas`);
  return parseJsonOrThrow(response);
}

export async function crearTarea(solicitudId, { nombre, descripcion, responsableId, estaCompleta }) {
  const response = await fetch(`${API_BASE_URL}/api/solicitudes/${solicitudId}/tareas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre, descripcion, responsable_id: responsableId, esta_completa: estaCompleta }),
  });
  return parseJsonOrThrow(response);
}

export async function actualizarTarea(tareaId, { nombre, descripcion, responsableId, estaCompleta }) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre, descripcion, responsable_id: responsableId, esta_completa: estaCompleta }),
  });
  return parseJsonOrThrow(response);
}

export async function eliminarTarea(tareaId) {
  const response = await fetch(`${API_BASE_URL}/api/tareas/${tareaId}`, { method: "DELETE" });
  if (!response.ok) {
    await parseJsonOrThrow(response);
  }
}

export async function crearSolicitudFormulario({
  solicitanteEmail,
  titulo,
  descripcion,
  tipo,
  cliente,
  adjuntos,
}) {
  const formData = new FormData();
  formData.append("solicitante_email", solicitanteEmail);
  formData.append("titulo", titulo);
  formData.append("descripcion", descripcion);
  formData.append("tipo", tipo);
  if (cliente) {
    formData.append("cliente", cliente);
  }
  for (const archivo of adjuntos || []) {
    formData.append("files", archivo);
  }

  const response = await fetch(`${API_BASE_URL}/api/solicitudes/formulario`, {
    method: "POST",
    body: formData,
  });
  return parseJsonOrThrow(response);
}

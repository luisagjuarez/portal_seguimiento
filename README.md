# Portal de Seguimiento DOVELA

Sistema para gestionar requerimientos de software y tareas internas de los equipos de
tecnología de DOVELA (Fábrica de Software, Implementación, Mesa de Ayuda, Infraestructura,
Sysadmins & DBAs).

Este repositorio implementa tres canales de creación de solicitudes:

- **Módulo 1.1 — Ingestión por Correo:** un worker en Python que lee un buzón IMAP, detecta
  correos de "Nueva solicitud" y registra automáticamente la solicitud, guarda sus adjuntos y
  genera un documento `.md` estandarizado.
- **Fase 1.2 — Chat Web:** una API HTTP (FastAPI) + una SPA en React que permite registrar una
  solicitud respondiendo un wizard tipo chat (correo, título, descripción, cliente, adjuntos).
- **Fase 1.6 — Página de Solicitudes:** dentro de la misma SPA, un formulario tradicional (un
  solo paso, con adjuntos) para registrar solicitudes, más un listado con filtros
  (cliente/nombre/estatus) de las solicitudes existentes, mostradas como tarjetas.

Los tres canales escriben en la misma tabla de solicitudes y comparten la lógica de negocio
(detección/alta de cliente, generación del `.md`, guardado de adjuntos).

Roadmap completo en `00_ARCHIVOS/00_requerimiento.md`.

## Estructura

```
backend/
  app/email_ingest/  → worker de correo (Módulo 1.1)
  app/api/           → API HTTP (Fase 1.2 chat + Fase 1.6 formulario/listado/catálogos)
  app/db/, app/md_generator/, app/storage.py, app/config.py, app/models.py → compartido por los 3 canales
  main.py            → entrypoint del worker de correo
  api_main.py        → entrypoint de la API (uvicorn)
  sql/               → DDL, Dockerfile, tests
frontend/            → SPA en React + Vite (menú lateral: Inicio, Solicitud por Chat, Solicitudes), Dockerfile (nginx)
docker-compose.yml
data/nfs/            → NFS simulado en local (adjuntos y documentos .md), creado por docker-compose
```

## Integración con la base de datos PostgreSQL

La base de datos es **PostgreSQL** (base `dovela_control`, esquema `solicitudes`), corriendo
fuera de `docker-compose.yml` — es infraestructura ya provista, no un contenedor que este
proyecto gestione. Credenciales de referencia en `00_ARCHIVOS/conexion_db.json`.

El esquema `solicitudes` **ya existe y ya está poblado** con catálogos y datos de negocio
reales (`miembros_equipo`, `clientes`, `estatus`, `tipos_solicitud`, `canales_solicitud`,
`solicitudes`, y las tablas de Fase 2 `tareas`/`hitos`/`comentarios`/`tarea_por_hacer`/
`enlaces_tarea`, fuera del alcance de este módulo). Este proyecto **no las recrea**, se acopla
a ellas. `backend/sql/003_postgres_modulo_correo_chat.sql` es el único script pendiente de
correr contra ese esquema (ya se corrió durante la migración): agrega las tablas propias del
módulo — `adjuntos`, `solicitudes_adjuntos`, `solicitudes_md`, `emails_procesados` — que no
tienen equivalente en el esquema existente.

Los scripts DDL del diseño anterior (acoplado a Oracle/APEX) quedaron en
`backend/sql/oracle_legacy/` como referencia histórica; ya no se ejecutan.

### Decisiones de mapeo relevantes

- **Solicitante:** `solicitudes.solicitante` es un FK a `miembros_equipo(id)` — el
  solicitante SIEMPRE es un miembro del equipo DOVELA, nunca el cliente externo. Se resuelve
  buscando el email de quien mandó el correo o llenó el chat en
  `miembros_equipo.correo_electronico` (`repository.find_miembro_id_by_email`). Si no hay
  match, `solicitante` queda `NULL` para revisión manual — no se crea un miembro nuevo.
  **Nota:** hoy esa columna está vacía en las 12 filas de `miembros_equipo` (se perdió en una
  limpieza de columnas duplicadas de una importación CSV anterior); hasta que se repueble
  manualmente, todas las solicitudes entrantes quedarán con `solicitante=NULL`.
- **Cliente, tipo y canal:** `solicitudes.cliente`/`tipo`/`canal` son FKs numéricos a
  `clientes`/`tipos_solicitud`/`canales_solicitud` (a diferencia del diseño Oracle anterior,
  que los guardaba como texto libre). `repository.insert_solicitud` resuelve esos ids a
  partir de los valores de texto que ya maneja el resto del código
  (`NuevaSolicitud.cliente`/`tipo`/`canal_origen`). `canal_origen` interno `EMAIL`/`CHAT` se
  mapea a los nombres de catálogo `'Correo'`/`'Chatbot'`.
- **Cliente no identificado:** igual que antes, si no se identifica ningún cliente en el
  correo, `cliente` queda `NULL` para revisión manual — no se inventa uno.
- **Estatus:** `codigo_estatus` sigue siendo una FK por texto a `estatus.codigo` (sin cambios
  respecto al diseño anterior).
- **Título:** se le sigue agregando un folio corto (fecha + hash del `Message-ID`) por
  trazabilidad, aunque `solicitudes.nombre` ya no tiene una restricción `UNIQUE` en este
  esquema.
- **Auditoría (`creado_en`/`creado_por`/`actualizado_en`/`actualizado_por`):** este esquema no
  tiene triggers ni column defaults (a diferencia del trigger `BIU_EBA_DEMO_MD_PROJECTS` de
  Oracle) — `insert_solicitud` los llena explícitamente (`now()`/`current_user`).
- **Dedup de correos:** tabla `emails_procesados` para no reprocesar el mismo correo si el
  worker se reinicia a medio proceso.
- **Secuencias de `IDENTITY`:** las tablas del esquema se poblaron originalmente con ids
  explícitos (import masivo), lo que deja la secuencia interna del `GENERATED BY DEFAULT AS
  IDENTITY` desincronizada (arranca en 1 y choca con ids ya existentes). Se corrigió una vez
  con `setval(...)` sobre `solicitudes`, `clientes`, `miembros_equipo` y `tipos_solicitud`; si
  se vuelve a cargar el esquema desde una exportación similar, hay que repetir ese ajuste.
- Limitación conocida del MVP: si la transacción de una solicitud falla después de haber
  guardado adjuntos o el `.md` en disco pero antes del `COMMIT`, esos archivos quedan
  huérfanos (la fila en BD sí se revierte). No afecta la integridad de los datos, solo deja
  archivos sin referenciar.

## Chat web (Fase 1.2)

API HTTP (FastAPI, `backend/app/api/`) + SPA en React (`frontend/`):

- `GET /api/health` — para probes.
- `GET /api/clientes?q=<texto>` — autocompletar del catálogo `CLIENTES` (usado por el paso
  "cliente" del wizard).
- `POST /api/solicitudes/chat` — crea la solicitud. `multipart/form-data`: campos
  `solicitante_email`, `titulo`, `descripcion`, `cliente` (opcional), y `files` (0 o más
  archivos adjuntos, opcional). Reutiliza exactamente la misma lógica de detección/alta de
  cliente, unicidad de título, guardado de adjuntos (`app/storage.py`, compartido con el
  worker de correo) y generación de `.md` que el canal de correo, con `CANAL_ORIGEN='CHAT'`.
  Límite de adjuntos (compartido con el formulario de la Fase 1.6): máx. 5 archivos, 10 MB
  cada uno (constantes `MAX_ADJUNTOS_POR_SOLICITUD`/`MAX_ADJUNTO_SIZE_BYTES` en
  `routes_solicitudes.py`) — el canal de correo no tiene este límite, ya está acotado a quien
  tenga acceso al buzón.

El frontend es una SPA de Vite; en Docker, la URL de la API (`API_BASE_URL`) se inyecta en
runtime (no en build time) vía `frontend/public/config.js` + `frontend/docker-entrypoint.sh`,
para que la misma imagen sirva para TEST y PRODUCCIÓN sin recompilar.

## Página de Solicitudes (Fase 1.6)

Tercer canal de creación, más un listado. Mismo patrón de transacción/adjuntos que el chat
(`_crear_solicitud_con_adjuntos`, helper compartido en `routes_solicitudes.py`), pero con
`tipo` y `solicitante` elegidos de catálogo en un formulario tradicional de un solo paso, en
vez de resueltos/asumidos implícitamente:

- `GET /api/solicitudes?cliente=&nombre=&estatus=` — listado con filtros (todos opcionales,
  `ILIKE` para cliente/nombre, igualdad exacta de código para estatus), más recientes primero,
  máx. 100 filas (`repository.list_solicitudes`).
- `GET /api/miembros-equipo`, `GET /api/tipos-solicitud`, `GET /api/estatus`
  (`backend/app/api/routes_catalogos.py`) — catálogos de solo lectura para poblar los
  `<select>` del formulario y el filtro de estatus.
- `POST /api/solicitudes/formulario` — mismo contrato multipart que `/solicitudes/chat`, más
  `tipo` (requerido, texto del catálogo `tipos_solicitud`). `solicitante_email` en este canal
  viene del `<select>` de miembros del equipo (su `value` es el email), pero se resuelve con
  la misma `find_miembro_id_by_email` que ya usan correo/chat — no hubo que tocar
  `repository.py` para esto. `canal_origen='FORMULARIO'` mapea a la fila `'Formulario'` que ya
  existía en el catálogo `canales_solicitud` (id=3) desde antes de esta fase.

En el frontend, `App.jsx` tiene un menú lateral (`Sidebar.jsx`, sin librería de routing —
navegación por estado simple) con tres secciones: Inicio (`InicioPage.jsx`), Solicitud por
Chat (el wizard de Fase 1.2 sin cambios) y Solicitudes (`SolicitudesPage.jsx`: filtros + grid
de tarjetas `SolicitudCard.jsx` + modal con `CrearSolicitudFormulario.jsx`). El picker de
adjuntos se extrajo a `AdjuntosInput.jsx` (componente controlado puro), reutilizado tanto por
el paso de adjuntos del chat (`AdjuntosPaso.jsx`, ahora un wrapper delgado) como por el
formulario nuevo.

**Importante:** los servicios `backend` y `api` en `docker-compose.yml` deben tener montados
los mismos volúmenes de `data/nfs/adjuntos` y `data/nfs/archivos_md` — si a alguno le falta,
los archivos que genera quedan solo en el filesystem efímero de ese contenedor y desaparecen
al recrearlo (bug real que se encontró y corrigió: el servicio `api` no los tenía).

## Configuración

1. Copia `backend/.env.example` a `.env` en la raíz del proyecto (mismo nivel que
   `docker-compose.yml`) y completa tus credenciales:

   ```bash
   cp backend/.env.example .env
   ```

2. Variables clave:

   | Variable | Descripción |
   |---|---|
   | `IMAP_HOST` / `IMAP_PORT` / `IMAP_USER` / `IMAP_PASSWORD` | Credenciales del buzón IMAP a monitorear |
   | `IMAP_MAILBOX` | Carpeta a revisar (default `INBOX`) |
   | `IMAP_USE_SSL` | `true`/`false` |
   | `IMAP_PROCESSED_FOLDER` | Carpeta opcional a la que mover correos ya procesados |
   | `SUBJECT_FILTER` | Texto que debe contener el Asunto (default `Nueva solicitud`) |
   | `POLL_INTERVAL_SECONDS` | Frecuencia de polling del buzón |
   | `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Conexión a PostgreSQL (`host.docker.internal` desde los contenedores, `localhost` si corres el backend directo en el host) |
   | `POSTGRES_SCHEMA` | Esquema donde vive todo (default `solicitudes`) |
   | `ATTACHMENTS_DIR` / `MD_DIR` | Rutas del NFS (real o simulado) para adjuntos y documentos `.md` |
   | `STATUS_CD_NUEVA` / `TIPO_NUEVA_SOLICITUD` | Valores por defecto al crear la solicitud |
   | `FRONTEND_ORIGIN` | Origen permitido por CORS en la API (default `http://localhost:5173`) |
   | `API_BASE_URL` (docker-compose, servicio `frontend`) | URL pública de la API que usará el navegador |

## Levantar backend + api + frontend (+ mailserver de pruebas)

La base de datos PostgreSQL corre aparte, fuera de este `docker-compose.yml` (ver
"Integración con la base de datos PostgreSQL" arriba). `docker-compose.yml` solo levanta la
aplicación:

```bash
# backend (worker de correo) + api + frontend
docker compose up -d

# + mailserver de pruebas (IMAP/SMTP falso, para probar el canal de correo sin credenciales reales)
docker compose --profile local-test up -d mailserver
```

Probar ambos canales:

```bash
# Canal correo: envía un correo de prueba (asunto "Nueva solicitud...", incluye
# "Cliente: Chantilly" y un adjunto) — requiere el mailserver de pruebas arriba
python backend/scripts/send_test_email.py
docker compose logs -f backend

# Canal chat: abre http://localhost:5173 y completa el wizard, o pruébalo por curl:
curl http://localhost:8000/api/health
curl "http://localhost:8000/api/clientes?q=chan"
curl -X POST http://localhost:8000/api/solicitudes/chat -H "Content-Type: application/json" \
  -d '{"solicitante_email":"tu@dovela.com","titulo":"Prueba","descripcion":"Detalle...","cliente":"Chantilly"}'
```

Verificación del resultado (ambos canales), conectándote a Postgres (ej. `psql` o
`docker run --rm --network host -e PGPASSWORD=... postgres:16-alpine psql -h localhost -U
$POSTGRES_USER -d $POSTGRES_DB`, con `SET search_path TO solicitudes;`):

- Debe existir una fila nueva en `solicitudes` por cada solicitud, con `tipo` resuelto (id de
  `tipos_solicitud`), `codigo_estatus='EN ESPERA'`, `canal` resuelto (id de
  `canales_solicitud`), `cliente` resuelto (id de `clientes`), y `solicitante` resuelto (id de
  `miembros_equipo`, o `NULL` si el email del remitente no coincide con ningún miembro).
- Correo: debe existir una fila en `emails_procesados` con el `Message-ID` del correo.
- Debe existir `data/nfs/archivos_md/<id>.md` (ambos canales) y, para el correo,
  `data/nfs/adjuntos/<id>/ejemplo_reporte.csv`, registrados en `solicitudes_md` y
  `adjuntos`/`solicitudes_adjuntos`.

Si el puerto `8000` (API) o algún otro ya está en uso en tu máquina por otro proyecto, usa un
override de `docker-compose` con un mapeo de puerto distinto y ajusta `API_BASE_URL` en
`.env` para que el frontend siga apuntando al puerto correcto.

## Tests unitarios

Backend — cubren `parser`, `client_matcher`, `title_synthesizer` y los endpoints de la API
(`app/api/routes_solicitudes.py`, con `app.db.repository`/`get_connection`/`release_connection`
monkeypatcheados, sin IMAP ni Postgres reales):

```bash
cd backend
pip install -r requirements.txt
pytest
```

Frontend — verificación mínima de compilación (no hay navegador en CI para probar la UI
interactivamente; prueba el wizard manualmente en `http://localhost:5173` o con los `curl`
de la sección anterior):

```bash
cd frontend
npm install
npm run build
```

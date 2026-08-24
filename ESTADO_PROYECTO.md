# Estado del proyecto — Portal de Seguimiento DOVELA

Última actualización: 2026-08-24

## Dónde vamos en el roadmap

```
[x] Fase 1.1 — Ingestión por Correo         ✅ implementado y verificado end-to-end (Postgres)
[x] Fase 1.2 — Chat Web                     ✅ implementado y verificado end-to-end (Postgres)
[ ] Fase 1.3 — Conexión ERP Oracle          ⬜ no iniciado (bloqueado además por auth IMAP M365, ver abajo)
[ ] Fase 1.4 — API pública de Solicitudes   ⬜ no iniciado (GET /api/solicitudes ya existe, ver Fase 1.6)
[ ] Fase 1.5 — Ingesta de archivos (txt/md/docx/pdf) ⬜ no iniciado
[x] Fase 1.6 — Página de Solicitudes (listado + formulario) ✅ implementado, verificado por API/tests
[x] Fase 1.7 (extraoficial) — Vista maestro-detalle, editar/borrar solicitud, CRUD de tareas ✅ implementado y verificado end-to-end (2026-08-23)
[ ] Fase 2   — Actualización de tareas      ⬜ no iniciado (parcialmente cubierto por el CRUD de tareas de la Fase 1.7, ver abajo)
[x] Fase 1.8 (extraoficial) — Autenticación, roles Scrum y borrado lógico ✅ implementado y verificado end-to-end (2026-08-23)
[x] Fase 1.9 (extraoficial) — Login obligatorio total, cambio forzado/autoservicio y recuperación de contraseña ✅ implementado y verificado end-to-end (2026-08-24)
```

**Cambio importante de arquitectura (2026-08-23, ampliado 2026-08-24):** el portal ya no es
de acceso libre. Hay login real (usuario/contraseña) sobre `miembros_equipo`, con 3 roles
Scrum (Product Owner, Scrum Master, Team) y una sola regla de permisos por ahora: **solo el
Scrum Master puede crear tareas**. Los borrados de solicitud/tarea/comentario/hito ya no son
físicos: son lógicos (`borrado_en`/`borrado_por`), y `creado_por`/`actualizado_por` ahora
guardan el `usuario` real de portal, no el rol de conexión a Postgres. Detalle completo en
`00_ARCHIVOS/BITACORAS/2026-08-23.md`.

**2026-08-24 — Login obligatorio en todo el portal (incluye Inicio y Solicitud por Chat):**
el 23 el login solo protegía las páginas internas (Solicitudes/Tablero/Usuarios/detalle);
"Inicio" y el wizard de "Solicitud por Chat" seguían siendo de acceso libre pensando en
solicitantes externos. El usuario pidió cerrar eso: ahora **todo** el portal exige sesión,
sin excepción (`frontend/src/App.jsx` ya no distingue páginas — si no hay `usuarioActual`,
se muestra `LoginPage` sin importar la página elegida). Como consecuencia, el wizard de chat
ya conoce quién es el solicitante: el primer paso (pedir el correo escribiéndolo a mano) se
quitó (`PASOS` en `ChatWindow.jsx` ya no incluye `"email"`), y el correo se toma directo de
`usuarioActual.correo_electronico` — nuevo campo expuesto en `GET /api/auth/me` y en la
respuesta de `POST /api/auth/login` (`UsuarioActualOut`, `UsuarioActual` en
`app/auth/dependencies.py`, columnas nuevas en `get_miembro_by_usuario`/`get_miembro_by_id`
de `repository.py`). Verificado en navegador con la sesión de `DOVELA_LG`: el chat arranca
directo en "¿Cuál es el título...?" y el resumen final muestra el correo real de sesión sin
haberlo preguntado.

**Pendiente para más adelante (anotado, no iniciado):** el usuario está contemplando un
**segundo portal, separado de este**, que exponga *solo* el wizard de "Solicitud por Chat"
para solicitantes externos (sin login de equipo DOVELA) — ahora que el portal principal cerró
el chat a solo usuarios internos autenticados, hace falta algún canal para quien no es del
equipo. Sin diseño todavía (¿subdominio aparte? ¿misma API con un endpoint público distinto?
¿reusa `POST /api/solicitudes/chat` tal cual?) — a definir con el usuario cuando lo retome.

**2026-08-24 (mismo día) — Sidebar oculto pre-login, cambio de contraseña forzado/
autoservicio, y recuperación por correo:** el usuario notó que el menú lateral con todas las
opciones del portal se veía incluso antes de iniciar sesión — se ocultó (`Sidebar` en
`App.jsx` ahora solo se renderiza si hay `usuarioActual`). Además pidió tres funcionalidades
de contraseña que no existían: forzar cambio en el primer acceso, recuperación por correo, y
cambio autoservicio ya logueado. Las tres quedaron implementadas — detalle completo del
diseño y la implementación en `00_ARCHIVOS/BITACORAS/2026-08-24.md` y en el plan
`/home/lg/.claude/plans/golden-wiggling-mitten.md`. Resumen:

- Nueva columna `miembros_equipo.debe_cambiar_password` (migración
  `backend/sql/007_password_reset.sql`, corrida contra la BD real): se pone en `true` cada
  vez que el Scrum Master otorga acceso por primera vez o resetea la contraseña de alguien
  (`otorgar_acceso_miembro`/`actualizar_acceso_miembro` en `repository.py`); se limpia en
  cuanto el propio usuario fija su contraseña (reset por correo o autoservicio). **No se
  aplicó retroactivamente** a los 3 usuarios ya activos (`DOVELA_LG`, `DOVELA_WA`,
  `DOVELA_JC`) — nacen en `false`.
- `App.jsx` bloquea toda la app (sin sidebar) mostrando `CambiarPasswordFormulario
  obligatorio` mientras `usuarioActual.debe_cambiar_password` sea `true`.
- Recuperación por correo: nueva tabla `tokens_reset_password` (token hasheado con SHA-256,
  vence a los 30 min, un solo uso), endpoints `POST /api/auth/forgot-password` y
  `POST /api/auth/reset-password` (`routes_auth.py`), y nuevo módulo de envío
  `backend/app/email_send/mailer.py` (`smtplib` puro, sin dependencias nuevas). **El envío
  usa el mismo mailserver de pruebas (greenmail, `--profile local-test`, puerto 3025) que ya
  se usaba para IMAP — no hay SMTP real configurado.** Mismo tipo de pendiente que el bloqueo
  de IMAP M365: para producción hace falta un proveedor SMTP real y las variables `SMTP_*` en
  `.env` (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_USE_TLS`/`SMTP_FROM`,
  `RESET_TOKEN_EXPIRE_MINUTES`). El enlace del correo apunta a
  `{FRONTEND_ORIGIN}/?reset_token=...`; `App.jsx` lo detecta por query string al montar y
  muestra `ResetPasswordPage` sin pasar por login.
- Cambio autoservicio: `POST /api/auth/change-password` (exige contraseña actual), accesible
  desde un botón "Cambiar contraseña" nuevo en el sidebar (`pagina = "cambiar-password"`).
  Devuelve `400` (no `401`) si la contraseña actual es incorrecta, a propósito — un `401`
  hubiera disparado el logout automático del interceptor global de `api.js` ante un simple
  typo.
- Verificado end-to-end en navegador y por `curl`: sidebar ausente antes de login; a
  `DOVELA_AR` se le otorgó acceso de prueba y su login cayó directo en la pantalla
  obligatoria (sin sidebar), completó el cambio y pasó a "Inicio" sin volver a loguearse;
  recuperación por correo probada de punta a punta leyendo el mailserver de pruebas por IMAP
  (`localhost:3143`) para extraer el link real y completar el reset; cambio autoservicio
  probado con `DOVELA_LG`. El usuario de prueba (`DOVELA_AR`) quedó restaurado a
  `acceso_activo=false` al terminar, y la contraseña de `DOVELA_LG` quedó de nuevo en
  `DovelaScrum2026!` (la ya documentada arriba). 89 tests de backend en verde (17 nuevos).

**Credenciales creadas durante la implementación (pendiente que el usuario las cambie o
las tome nota):** `DOVELA_LG` (Scrum Master) → `DovelaScrum2026!`. También se otorgó
acceso de prueba a `DOVELA_WA` (Team) → `ClaveInicial2026!` y `DOVELA_JC` (Product Owner)
→ `ClaveJC2026!` — el resto de los 12 miembros del equipo siguen sin acceso
(`acceso_activo=false`) hasta que el Scrum Master se los otorgue desde la página
"Usuarios".

A partir de esta sesión, el detalle de cada tarea trabajada se registra en
`00_ARCHIVOS/BITACORAS/AAAA-MM-DD.md` (un archivo por día). Este documento sigue siendo la
referencia estable del estado general del roadmap.

Roadmap completo y contexto de negocio: `00_ARCHIVOS/00_requerimiento.md`.

## Cambio de persistencia: Oracle → PostgreSQL (2026-08-21)

Las Fases 1.1 y 1.2 se construyeron originalmente acopladas a tablas Oracle ya existentes de
una app APEX (`CLIENTES`, `EBA_DEMO_MD_PROJECTS`). El 2026-08-21 se migró la persistencia a
**PostgreSQL**: base `dovela_control`, esquema `solicitudes` (credenciales en
`00_ARCHIVOS/conexion_db.json`), corriendo en un contenedor Docker externo
(`postgres_db`, `postgres:16-alpine`, puerto 5432 del host) **no gestionado por
`docker-compose.yml`** de este proyecto.

A diferencia del intento original de diseñar un esquema mínimo desde cero, el esquema
`solicitudes` **ya existía y ya estaba poblado** con datos de negocio reales (12 miembros del
equipo, 15 clientes, catálogos de estatus/tipos/canales, y 47 solicitudes ya cargadas) cuando
se hizo el análisis. La app se adaptó a ese esquema real, no al revés. Detalles completos del
mapeo en `README.md` (sección "Integración con la base de datos PostgreSQL").

Cambios de código relevantes:
- Driver `oracledb` → `psycopg` (v3, con `psycopg_pool`).
- `backend/app/db/repository.py`: reescrito para el esquema real — `solicitante`/`cliente`/
  `tipo`/`canal` ahora son FKs numéricas (antes texto libre u otro diseño), resueltas en
  `insert_solicitud` a partir de los mismos campos de texto que ya manejaba el resto del
  código. Nuevo: `find_miembro_id_by_email` resuelve el solicitante por el email del
  remitente (correo o chat) contra `miembros_equipo` — el solicitante siempre es alguien del
  equipo DOVELA, nunca el cliente externo.
- Ya no hace falta el workaround de precisión de IDs de Oracle (`cursor.var(int)` vs
  `SYS_GUID()`): Postgres genera `bigint` normales vía `IDENTITY` + `RETURNING id`.
- `docker-compose.yml`: se quitó el servicio `oracle-db`; `backend`/`api` usan
  `extra_hosts: host.docker.internal` para alcanzar el Postgres del host.
- DDL Oracle anterior movido a `backend/sql/oracle_legacy/` (referencia histórica, ya no se
  ejecuta). Nuevo `backend/sql/003_postgres_modulo_correo_chat.sql` agrega las tablas propias
  del módulo (`adjuntos`, `solicitudes_adjuntos`, `solicitudes_md`, `emails_procesados`) sobre
  el esquema existente — ya se corrió contra la BD real.

**Pendiente de datos (no es un bug de código):** `miembros_equipo.correo_electronico` está
vacía en las 12 filas actuales — se perdió el dato en una limpieza de columnas duplicadas de
una importación CSV anterior, hecha fuera de esta sesión, antes de hacer el backfill. Hasta
que el usuario la repueble manualmente, toda solicitud entrante (correo o chat) queda con
`solicitante=NULL` — comportamiento esperado y seguro (no falla la request), pero sin
atribución real de quién la levantó.

También se corrigieron las secuencias de `IDENTITY` de `solicitudes`, `clientes`,
`miembros_equipo` y `tipos_solicitud` (quedaron desincronizadas por la carga masiva inicial
con ids explícitos — sin este ajuste, cualquier INSERT nuevo colisionaba con ids ya
existentes).

## Fix de volumen + adjuntos en el chat (2026-08-21, misma tarde)

Al probar el chat manualmente, el usuario notó que el `.md` no aparecía en disco. Causa real:
el servicio `api` en `docker-compose.yml` **nunca tuvo montados** los volúmenes
`data/nfs/adjuntos`/`data/nfs/archivos_md` (a diferencia de `backend`, que sí los tenía) — el
archivo se generaba pero quedaba en el filesystem efímero del contenedor `api` y se perdía en
cada recreate. Bug preexistente de la Fase 1.2, no introducido por la migración. Corregido:
mismos `volumes:` en el servicio `api`; verificado con una solicitud nueva (`id=53`).

De paso se agregó la funcionalidad de **adjuntar archivos desde el chat** (antes solo existía
para el canal de correo):
- `POST /api/solicitudes/chat` pasó de JSON a `multipart/form-data` (campo `files`, 0 o más
  archivos). Límite: máx. 5 archivos, 10 MB c/u (`MAX_ADJUNTOS_CHAT`/`MAX_ADJUNTO_SIZE_BYTES`
  en `backend/app/api/routes_solicitudes.py`) — el canal de correo no tiene este límite.
- El guardado a disco (antes privado en `listener.py`) se extrajo a
  `backend/app/storage.py` (`save_attachment`), compartido por ambos canales.
- Frontend: nuevo paso "adjuntos" en el wizard (`frontend/src/components/AdjuntosPaso.jsx`),
  entre "cliente" y "resumen" — selección de 0 o más archivos, opción de quitar cada uno antes
  de confirmar. `frontend/src/api.js` arma `FormData` en vez de JSON.
- Tests nuevos en `backend/tests/test_api_solicitudes.py` (adjuntos ok, rechazo por cantidad,
  rechazo por tamaño); los 3 tests existentes del endpoint de chat se migraron de `json=` a
  `data=` (multipart) porque el contrato de la API cambió.
- Verificado end-to-end por `curl` (con adjunto, sin adjuntar, 6 archivos rechazados con 422)
  y confirmado en disco (`data/nfs/adjuntos/<id>/`), en BD (`adjuntos`/`solicitudes_adjuntos`)
  y en el `.md` generado.

## Fase 1.6 — Página de Solicitudes: listado + formulario tradicional (2026-08-21)

Tercera forma de registrar solicitudes, pedida explícitamente por el usuario: un formulario
tradicional (un solo paso, no wizard) accesible desde una nueva página "Solicitudes" que
también lista las solicitudes existentes como tarjetas, con filtros por cliente/nombre/estatus.
Se agregó además un menú lateral (Inicio, Solicitud por Chat, Solicitudes) — el frontend deja
de ser una sola pantalla.

Hallazgo útil: `canales_solicitud` ya tenía una fila `'Formulario'` (id=3) en el catálogo —
este canal ya estaba previsto en el diseño de la BD, solo faltaba construirlo. **No hizo falta
ningún cambio de esquema/DDL** para esta fase.

- Backend: nuevo endpoint `POST /api/solicitudes/formulario` (mismo patrón multipart/adjuntos
  que el chat, pero con `tipo` y `solicitante` elegidos de catálogo en vez de
  asumidos/resueltos por email de forma implícita — aunque `solicitante` se sigue resolviendo
  por email internamente, el `<select>` del formulario simplemente manda el email como value).
  La lógica de crear-solicitud-con-adjuntos se extrajo a un helper compartido
  (`_crear_solicitud_con_adjuntos` en `routes_solicitudes.py`) para no triplicarla entre
  chat/formulario. Nuevo `GET /api/solicitudes` (listado con filtros `cliente`/`nombre`/
  `estatus`, `repository.list_solicitudes`) y `backend/app/api/routes_catalogos.py` con
  `GET /api/miembros-equipo`, `GET /api/tipos-solicitud`, `GET /api/estatus` para poblar los
  `<select>`/filtros.
- Frontend: `App.jsx` pasa a tener un layout de sidebar (sin librería de routing — navegación
  por estado simple, consistente con el resto del proyecto que evita dependencias extra).
  Nuevas páginas `InicioPage.jsx`, `SolicitudesPage.jsx` (filtros + grid de tarjetas
  `SolicitudCard.jsx` + modal con `CrearSolicitudFormulario.jsx`). `AdjuntosPaso.jsx` (del
  chat) se separó en un `AdjuntosInput.jsx` reutilizable, usado tanto por el wizard de chat
  como por el formulario nuevo.
- Verificado por `curl`/tests: 30 tests de backend en verde (6 nuevos), `GET /api/solicitudes`
  con y sin filtros, `POST /api/solicitudes/formulario` con adjunto → fila real con
  `canal=Formulario`, `tipo` y `solicitante` resueltos correctamente (confirmado en BD).
  **Falta la pasada visual en navegador** (el usuario la hará a continuación).

## Fase 1.7 (extraoficial) — Vista maestro-detalle, editar/borrar solicitud, CRUD de tareas (2026-08-23)

Implementado siguiendo `00_ARCHIVOS/PROMPTS/00_Solicitud-Edicion-Prompt.md`, en modo plan
(plan en `/home/lg/.claude/plans/fancy-questing-parnas.md`). Detalle completo del trabajo en
`00_ARCHIVOS/BITACORAS/2026-08-23.md`.

- **Backend**: `GET/PUT/DELETE /api/solicitudes/{id}`, `GET/POST /api/solicitudes/{id}/tareas`
  (en `routes_solicitudes.py`) y nuevo router `routes_tareas.py` con
  `PUT/DELETE /api/tareas/{id}`. Nuevas funciones en `repository.py`
  (`get_solicitud_by_id`, `update_solicitud`, `delete_solicitud`, `list_tareas_by_solicitud`,
  `insert_tarea`, `update_tarea`, `get_tarea_by_id`, `delete_tarea`) y schemas
  (`SolicitudDetalle`, `SolicitudUpdate`, `TareaOut`, `TareaCreateUpdate`). CORS ampliado a
  `PUT`/`DELETE` en `app.py` (antes solo `GET`/`POST`, bloqueaba estas llamadas).
- **Frontend**: nueva página `SolicitudDetallePage.jsx` (llegada al hacer clic en una
  `SolicitudCard`), `EditarSolicitudFormulario.jsx`, `TareaFormulario.jsx`, `TareaItem.jsx`,
  `ConfirmModal.jsx` (reutilizado para borrar solicitud y borrar tarea). `App.jsx` con nuevo
  estado de navegación `"solicitud-detalle"`.
- **Decisión de negocio tomada con el usuario:** borrar una solicitud borra sus filas de BD
  (adjuntos, `.md`, tareas, etc.) pero deja los archivos físicos huérfanos en disco a
  propósito (más seguro/recuperable) — no se tocó `app/storage.py` para esto.
- **Hallazgo crítico corregido:** las FKs de `solicitudes_adjuntos`, `solicitudes_md` y
  `emails_procesados` hacia `solicitudes(id)` no tenían `ON DELETE CASCADE` (a diferencia de
  `tareas`/`hitos`/`comentarios`/etc.) — un `DELETE` de solicitud fallaba por violación de FK
  en casi todos los casos reales. `delete_solicitud` ahora borra esas filas explícitamente
  antes de borrar la solicitud.
- **Otro hallazgo corregido:** la secuencia `solicitudes.tareas_id_seq` estaba desincronizada
  (mismo problema que ya se había corregido para otras tablas en la migración a Postgres,
  pero se pasó por alto en `tareas`) — 57 filas precargadas pero la secuencia seguía en 1.
  Corregida con `setval`. `hitos` se revisó también (vacía, sin problema todavía).
- **Verificado**: 42 tests unitarios en verde (36 existentes + 6 nuevos), verificación manual
  contra la BD real por `curl` (incluye borrar una solicitud con adjunto real, confirmando el
  fix de FKs), y verificación visual completa en navegador (Chrome) del flujo end-to-end:
  crear/editar/borrar tarea, editar solicitud (incl. cambio de estatus), borrar solicitud.

Esto cubre buena parte de lo que estaba previsto para la **Fase 2 (Actualización de
tareas)** del roadmap original — falta confirmar con el usuario si algo de esa fase queda
pendiente además de este CRUD básico (p. ej. horas estimadas/reales, hitos, enlaces entre
tareas, que ya existen en el esquema pero no se expusieron en la UI por no estar en el
alcance del prompt de esta sesión).

## Qué existe hoy

- **Backend** (`backend/`): dos procesos que comparten el mismo código de dominio
  (`app/config.py`, `app/models.py`, `app/db/`, `app/md_generator/`, `app/storage.py`):
  - `main.py` → `app/email_ingest/` — worker de polling IMAP (Fase 1.1).
  - `api_main.py` → `app/api/` — API FastAPI (Fase 1.2 + 1.6):
    `GET /api/health`, `GET /api/clientes?q=`, `GET /api/solicitudes` (listado con filtros y
    `orden_por`), `POST /api/solicitudes/chat` y `POST /api/solicitudes/formulario` (ambos
    multipart, con adjuntos opcionales; el de formulario también pide `canal` y admite
    `orden_prioridad`), `PUT /api/solicitudes/{id}` (incluye canal/orden_prioridad/
    fecha_completado, esta última obligatoria si el estatus es Completado), y
    `routes_catalogos.py` (`GET /api/miembros-equipo`, `GET /api/tipos-solicitud`,
    `GET /api/canales-solicitud`, `GET /api/estatus`).
- **Frontend** (`frontend/`): SPA en React + Vite con menú lateral (Inicio, Solicitud por
  Chat, Solicitudes). "Solicitud por Chat" es el wizard original (correo → título →
  descripción → cliente → adjuntos opcionales → confirmar). "Solicitudes" lista las
  existentes como tarjetas con filtros (cliente/nombre/estatus) y un botón "Crear solicitud"
  que abre un formulario tradicional de un solo paso (con adjuntos también). Se sirve con
  nginx en Docker; la URL de la API se inyecta en runtime vía `public/config.js` +
  `docker-entrypoint.sh`. Soporta modo oscuro/claro (toggle en el encabezado, persistido en
  `localStorage`, ver `00_ARCHIVOS/BITACORAS/2026-08-24.md`).
- **Base de datos**: PostgreSQL, esquema `solicitudes` (ver sección de migración arriba y
  `README.md` para el detalle completo del mapeo de columnas/catálogos).
- **Docker**: `docker-compose.yml` con `backend`, `api`, `frontend`, y `mailserver` (greenmail,
  perfil `local-test`). La BD Postgres es externa, no gestionada por este compose. `backend` y
  `api` deben tener los mismos volúmenes de `data/nfs/` montados (ver fix arriba).
- **Tests**: 94 tests unitarios en `backend/tests/` (parser, client_matcher,
  title_synthesizer, auth, endpoints de solicitudes incl. adjuntos/formulario/orden_por,
  endpoints de catálogos) — todos pasan. Frontend solo verificado con `npm run build` (sin tests
  automatizados todavía).

Detalles de configuración y comandos: `README.md`. Detalle de diseño y decisiones de cada
fase: `00_ARCHIVOS/Fase_01.md` (Fase 1.1) y el plan de Fase 1.2 (ver sección "Dónde quedó
guardado el plan" abajo). El plan de la migración a Postgres quedó en
`/home/lg/.claude/plans/mighty-wobbling-frost.md`.

## Verificación ya realizada (importante: no es solo teoría)

Se probaron ambos canales de punta a punta contra el Postgres real (`dovela_control`,
esquema `solicitudes`):
- Chat: `POST /api/solicitudes/chat` por `curl` → solicitud id=48 creada con `canal=2`
  (Chatbot), `cliente=10` (CHANTILLY), `tipo=3` (Nuevo), `.md` generado.
- Correo: `backend/scripts/send_test_email.py` (vía `mailserver` greenmail) → solicitud id=49
  creada con `canal=1` (Correo), adjunto guardado (`ejemplo_reporte.csv`), fila en
  `emails_procesados`, `.md` generado.
- Ambas filas de prueba (48 y 49) se dejaron en la BD real a petición del usuario, como
  evidencia de la migración.

**Actualización 2026-08-21 (tarde/noche):** el usuario sí probó el wizard de chat en un
navegador real (`http://localhost:5173`), incluyendo el paso de adjuntos — funcionó
correctamente después de dos fixes (ver sección "Fix de volumen + adjuntos en el chat"
arriba y el bug de `api.js` descrito abajo). `miembros_equipo.correo_electronico` ya fue
repoblada por el usuario con los emails reales del equipo — la resolución de `solicitante`
por email ya funciona en ambos canales (confirmado con Ramon Rosales id=6 y Victor Castañeda
id=8).

**Bug adicional encontrado y corregido al probar en navegador:** `frontend/src/api.js`
(`parseJsonOrThrow`) hacía `new Error(detail)` asumiendo que `detail` siempre era texto, pero
FastAPI manda los errores de validación (422) como una **lista** de objetos
`{loc, msg, type}` — JavaScript los convertía en el mensaje ilegible
`"[object Object],[object Object],[object Object]"`. Corregido para extraer `.msg` de cada
error. También se mejoró la UI del paso de adjuntos (antes era un `<input type="file">` sin
texto ni estilo, fácil de no ver) con un botón visible "Elegir archivo(s)...".

**Intento de conexión IMAP real (M365) — bloqueado por política del tenant:** se probó contra
`outlook.office365.com:993` con credenciales reales del usuario y falló con
`"Basic authentication is disabled."` — el tenant de Microsoft 365 tiene desactivada la
autenticación básica IMAP (comportamiento por defecto desde 2022 en la mayoría de tenants). El
worker actual (`imaplib` con usuario/contraseña) no puede conectarse mientras esa política siga
así. Opciones, pendientes de decisión del usuario:
1. Pedir a un admin de M365 que reactive una *Authentication Policy* de IMAP básico solo para
   el buzón de solicitudes (sin cambios de código).
2. Implementar OAuth2 (XOAUTH2) en `backend/app/email_ingest/listener.py` — requiere registrar
   una app en Azure AD y un flujo de token, cambio de código real.

Por ahora `.env` sigue apuntando al buzón de pruebas local (`greenmail`, `IMAP_HOST=mailserver`)
y el canal de correo se sigue verificando ahí (última prueba: solicitud id=58, remitente Victor
Castañeda, `canal=1`).

## Pendientes / próximos pasos sugeridos

1. **⭐ Otorgar acceso al resto del equipo.** Solo `DOVELA_LG` (Scrum Master), `DOVELA_WA`
   (Team, contraseña de prueba) y `DOVELA_JC` (Product Owner, contraseña de prueba) tienen
   acceso activo hoy. Los otros 9 miembros siguen con `acceso_activo=false`. `DOVELA_LG`
   puede otorgárselo desde la página "Usuarios" del portal. Ver también la nota de
   contraseñas de prueba más abajo — conviene cambiarlas o rotarlas.
2. Confirmar con el usuario si la única regla de permisos actual (crear tarea → solo Scrum
   Master) es suficiente, o si se quieren reglas más finas por rol para otras acciones
   (editar/borrar solicitud o tarea, hitos, comentarios) — hoy cualquier usuario logueado
   puede hacer todo lo demás.
3. Resolver la conexión IMAP real de M365 (ver bloqueo de autenticación básica arriba) —
   decidir entre pedir el cambio de política al admin o implementar OAuth2.
4. Decidir si seguimos con **Fase 1.3 (conexión al ERP Oracle de Mesa de Ayuda)**, **Fase 1.4
   (API pública)** — parte ya construida con `GET /api/solicitudes` y ahora también
   `GET/PUT/DELETE /api/solicitudes/{id}` — o **Fase 1.5** del roadmap.
5. Considerar tests automatizados de frontend (hoy solo se verifica con `npm run build` +
   verificación manual en navegador).
6. Deuda técnica menor: `miembros_equipo` conserva las columnas basura `usurio` y
   `correo_electrónico` (con tilde) de la importación CSV original — limpieza cosmética, no
   bloqueante.
7. Revisar si otras tablas con carga inicial masiva (además de `tareas`, ya corregida en la
   Fase 1.7) tienen la secuencia `IDENTITY` desincronizada antes de que alguien intente
   insertar en ellas por primera vez desde la app.
8. **Segundo portal para solicitantes externos (anotado 2026-08-24, sin diseñar).** Ahora
   que "Solicitud por Chat" exige login de equipo DOVELA, ya no hay canal web para quien no
   es del equipo (el correo y la ingesta por email siguen siendo la única vía externa hoy).
   El usuario quiere un portal aparte, más adelante, que exponga solo el wizard de chat para
   externos. Falta definir arquitectura (¿app/subdominio separado? ¿mismo backend con un
   endpoint público distinto al de `POST /api/solicitudes/chat` actual, que ahora asume un
   solicitante interno?).
9. **⭐ Conseguir SMTP real para recuperación de contraseña (anotado 2026-08-24).** El correo
   de "olvidé mi contraseña" hoy se envía contra el mailserver de pruebas (`greenmail`,
   `--profile local-test`, puerto 3025) — funciona en este entorno pero **no envía nada fuera
   de él**. Hace falta un proveedor SMTP real (¿M365/Graph, igual que se evaluó para el IMAP
   de entrada? ¿otro proveedor?) y completar `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/
   `SMTP_PASSWORD`/`SMTP_USE_TLS`/`SMTP_FROM` en `.env` — sin cambios de código, el módulo
   `backend/app/email_send/mailer.py` ya es agnóstico al proveedor.
10. Considerar si conviene forzar `debe_cambiar_password = true` también para los 3 usuarios
    ya activos hoy (`DOVELA_LG`, `DOVELA_WA`, `DOVELA_JC`), ya que sus contraseñas actuales
    quedaron documentadas en texto plano en este mismo archivo — un simple `UPDATE` cuando el
    usuario lo pida.

## Dónde quedó guardado el plan de la Fase 1.2

El plan detallado (contexto, diseño de la API, del chat y de la columna `CANAL_ORIGEN`) se
escribió durante la sesión en `/home/lg/.claude/plans/lively-growing-aho.md`. Ese archivo
puede sobrescribirse en sesiones futuras de planificación; este `ESTADO_PROYECTO.md` es la
referencia estable para continuar el proyecto.

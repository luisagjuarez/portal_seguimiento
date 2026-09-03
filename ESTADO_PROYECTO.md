# Estado del proyecto — Portal de Seguimiento DOVELA

Última actualización: 2026-09-03 (Fases 1.17-1.21 con pasada visual del usuario; dos ajustes de notificaciones/permisos aplicados, falta verificación e2e con curl/navegador)

## Dónde vamos en el roadmap

```
[x] Fase 1.1 — Ingestión por Correo         ✅ implementado y verificado end-to-end (Postgres)
[x] Fase 1.2 — Chat Web                     ✅ implementado y verificado end-to-end (Postgres)
[x] Fase 1.6 — Página de Solicitudes (listado + formulario) ✅ implementado, verificado por API/tests
[x] Fase 1.7 (extraoficial) — Vista maestro-detalle, editar/borrar solicitud, CRUD de tareas ✅ implementado y verificado end-to-end (2026-08-23)
[x] Fase 1.8 (extraoficial) — Autenticación, roles Scrum y borrado lógico ✅ implementado y verificado end-to-end (2026-08-23)
[x] Fase 1.9 (extraoficial) — Login obligatorio total, cambio forzado/autoservicio y recuperación de contraseña ✅ implementado y verificado end-to-end (2026-08-24)
[x] Fase 1.10 (extraoficial) — Módulo de gestión de usuarios (alta/baja/actualización) ✅ implementado y verificado end-to-end (2026-08-26)
[x] Fase 1.11 (extraoficial) — "Por hacer" en tareas (tabla tarea_por_hacer)          ✅ implementado y verificado end-to-end (2026-08-26)
[x] Fase 1.12 (extraoficial) — Monitor de tareas con indicadores para Scrum Master y Product Owner ✅ implementado y verificado end-to-end (2026-08-26)
[x] Fase 1.13 (extraoficial) — Reglas de permisos más finas por rol (borrar solo Scrum Master, editar/borrar propio en comentarios/hitos/"por hacer") ✅ implementado y verificado end-to-end (2026-08-27)
[x] Fase 1.14 (extraoficial) — Publicar el portal bajo el subpath /dovela_control ✅ implementado y verificado end-to-end en local y TEST (2026-08-27)
[x] Fase 1.15 (extraoficial) — Tablero de Dirección General (KPIs por rango de fechas, desglosados por cliente/tipo/área/estatus) ✅ implementado, verificado en navegador y desplegado en TEST (2026-09-01)
[~] Fase 1.16 (extraoficial) — Subvistas de detalle por métrica en Dirección General (mosaico + pies por cliente/área + tabla de solicitudes) — implementado y verificado visualmente por el usuario (2026-09-03); falta el deploy a TEST
[~] Fase 1.17 (extraoficial) — Semáforo de prioridad (1-5) heredado en tareas — implementado y verificado visualmente por el usuario (2026-09-03); falta el deploy a TEST
[~] Fase 1.18 (extraoficial) — Fecha de entrega + responsable de atención (obligatorios desde "Planeado") + semáforo de vencimiento — implementado y verificado visualmente por el usuario (2026-09-03); falta el deploy a TEST
[~] Fase 1.19 (extraoficial) — Filtros por defecto "mis tareas"/"mis solicitudes" en Tablero y Solicitudes — implementado y verificado visualmente por el usuario (2026-09-03); falta el deploy a TEST
[~] Fase 1.20 (extraoficial) — Notificaciones in-app + menciones @ en comentarios — implementado y verificado visualmente por el usuario (2026-09-03); con 2 ajustes tras la pasada visual (auto-notificación y permiso de creación de tareas, ver entrada 2026-09-03) verificados por 180 tests de backend; falta verificación e2e con curl/navegador de esos 2 ajustes y el deploy a TEST
[~] Fase 1.21 (extraoficial) — Agregar adjuntos a una solicitud ya creada + adjuntos en tareas (desde cero) — implementado y verificado visualmente por el usuario (2026-09-03); falta el deploy a TEST
```

**2026-09-03 — Pasada visual del usuario (Fases 1.16-1.21) y dos ajustes de
notificaciones/permisos:** el usuario recorrió el checklist de verificación visual pendiente
directamente en su navegador (sin necesitar que se condujera el navegador por él). Todo quedó
bien salvo dos preguntas sobre la Fase 1.20 que se convirtieron en ajustes:

1. **Auto-notificación**: la Fase 1.20 excluía a propósito al propio actor como destinatario de
   sus 4 disparadores (asignarse una tarea, asignarse responsable de atención de una solicitud,
   asignarse un "por hacer", mencionarse a sí mismo con `@usuario` en un comentario). El usuario
   pidió invertirlo: ahora sí llega la notificación en los 4 casos. Se quitaron las 5 condiciones
   `!= usuario_actual.id` / `discard(usuario_actual.id)` correspondientes en
   `routes_tareas.py`/`routes_solicitudes.py`. De paso se confirmó (sin cambios) que las
   notificaciones son asíncronas por polling cada 30s (`NotificacionesBell.jsx`), no en tiempo
   real — no hay websockets en el proyecto.
2. **Permiso de creación de tareas**: `POST /solicitudes/{id}/tareas` estaba restringido a
   `require_scrum_master` desde su origen, sin relación con el responsable de atención agregado
   en la Fase 1.18. El usuario pidió que el responsable de atención de una solicitud —que puede
   ser cualquier miembro del equipo, no un rol fijo— también pueda crear tareas y asignarlas a
   cualquier miembro (esto último ya funcionaba sin restricción). Nueva regla
   `require_scrum_master_o_responsable_solicitud` en `app/auth/dependencies.py` (no puede ser un
   `Depends`, el responsable solo se conoce tras leer la solicitud dentro del endpoint, mismo
   patrón que `require_autor_o_scrum_master`); `crear_tarea` ahora lee la solicitud primero (404
   si no existe) y aplica la regla. Frontend: `SolicitudDetallePage` recibe `usuarioActual` y
   muestra "Agregar Tarea" también si `usuarioActual.id === solicitud.responsable_atencion_id`.
   Borrar tarea sigue siendo exclusivo del Scrum Master (Fase 1.13, sin cambios).

180 tests de backend en verde (5 nuevos). Se corrieron copiando `backend/app`/`backend/tests` al
contenedor `api` en ejecución (la imagen de producción no incluye `tests/`), y luego se
reconstruyeron `api`/`backend`/`frontend` de verdad con `docker compose build` + `up -d`.
**Falta verificación end-to-end con `curl`/navegador contra la BD real de estos 2 ajustes**
(no se hizo en esta sesión por no tener credenciales de prueba a mano) y el **deploy a TEST**
de las 6 sub-fases completas (1.16 a 1.21, todas ya verificadas visualmente).

De la pasada visual de estos 2 ajustes surgió un tercer detalle: el picker de menciones `@` en
comentarios (Fase 1.20, `ComentarioFormulario.jsx`) no tenía navegación por teclado, solo clic de
mouse. Se agregó `ArrowUp`/`ArrowDown` para moverse entre opciones, `Enter` para confirmar y
`Escape` para cerrar el picker, con la opción activa resaltada (`.mencion-picker-activa` en
`styles.css`). Verificado con `npm run build` y contenedor `frontend` reconstruido; falta la
pasada visual de este detalle puntual.

**2026-09-02 — Fase 1.21, multi-adjuntos (quinta y última sub-fase del plan
`/home/lg/.claude/plans/nifty-wishing-hopper.md`):** ya se podían adjuntar varios archivos de
una vez al CREAR una solicitud (`AdjuntosInput`, máx. 5, 10MB c/u) — el hueco real, confirmado
con el usuario, era (a) no poder agregar adjuntos a una solicitud ya creada, y (b) que las
tareas no tuvieran ningún soporte de adjuntos. Ambos resueltos:

- Nuevo `POST /api/solicitudes/{id}/adjuntos` (agrega a una ya creada; valida que
  existentes+nuevos no pase de 5) y tab "Adjuntos" de `SolicitudDetallePage` ahora tiene control
  de subida (antes solo listaba/descargaba).
- Adjuntos en tareas desde cero: tabla `tareas_adjuntos` (`backend/sql/014_adjuntos_tarea.sql`,
  mismo patrón N:M que `solicitudes_adjuntos`, corrida contra la BD real),
  `POST/GET /api/tareas/{id}/adjuntos` y `GET .../{adjunto_id}/descargar`. Nueva pestaña
  "Adjuntos" en `TareaDetallePage`, y `TareaFormulario` permite adjuntar también al crear la
  tarea (subida en un segundo paso tras crearla, mismo endpoint que "agregar después").
- El helper de validación de adjuntos (límites, lectura) se extrajo a
  `app/api/adjuntos_helpers.py`, compartido entre `routes_solicitudes.py` y `routes_tareas.py`
  (antes solo vivía en el primero).
- **Hallazgo importante:** `solicitudes.id` y `tareas.id` son secuencias independientes que sí
  pueden coincidir (se confirmó creando solicitud 74 y tarea 74 al mismo tiempo) — guardar los
  adjuntos de tarea en la misma ruta que los de solicitud (`adjuntos/<id>/`) los habría
  sobreescrito entre sí. Se corrigió agregando un parámetro `subdir` a
  `app/storage.py:save_attachment` (`adjuntos/tareas/<id>/` para tareas, sin cambiar la ruta ya
  usada por solicitudes) — verificado en disco que ambos conjuntos de archivos con el mismo id
  conviven sin pisarse.
- Se expuso `usuario` en `GET /api/miembros-equipo` (aprovechado también por el picker de
  menciones de la Fase 1.20).

175 tests de backend en verde (9 nuevos). Verificado por `curl` contra la BD real: agregar un
adjunto a una solicitud ya creada, crear una tarea y agregarle un adjunto, descargar ambos
confirmando que no se pisaron en disco pese a compartir id, y rechazo 422 al intentar pasar de 5
adjuntos en una tarea. Datos y archivos de prueba borrados (incluida la carpeta en disco, vía
`docker exec` por permisos de root del contenedor). Reconstruidos y reiniciados los contenedores
`api`/`frontend` locales con este código.

**Con esto quedan implementadas y verificadas por tests/curl las 5 sub-fases del flujo
Solicitud-Tarea pedido por el usuario (semáforo de prioridad, fecha de entrega/responsable de
atención + semáforo de vencimiento, filtros por defecto, notificaciones + menciones, y
multi-adjuntos). Falta la pasada visual en navegador de las 5 antes de dar por cerrada la
iniciativa completa — ver sección "Pendientes" abajo.**

**2026-09-02 — Fase 1.20, notificaciones + menciones @ (cuarta de 5 sub-fases del plan
`/home/lg/.claude/plans/nifty-wishing-hopper.md`):** no existía absolutamente nada de
notificaciones (grep exhaustivo, cero resultados). Nueva tabla `notificaciones`
(`backend/sql/013_notificaciones.sql`, corrida contra la BD real: `destinatario_id`, `tipo`,
`mensaje`, `entidad_tipo`/`entidad_id` para armar el link, `leido_en` nullable = no leída).
Nuevo router `routes_notificaciones.py` (`GET /api/notificaciones`,
`GET /api/notificaciones/no-leidas/count`, `PUT /api/notificaciones/{id}/leer` — solo el propio
destinatario puede marcarla, `PUT /api/notificaciones/leer-todas`). Disparadores agregados
inline (misma transacción) en los endpoints ya existentes, comparando contra el estado anterior
para no notificar si el responsable no cambió ni notificarse a sí mismo:
- Asignar/reasignar responsable de una tarea (`POST/PUT /solicitudes/{id}/tareas`,
  `/tareas/{id}`) → tipo `TAREA_ASIGNADA`.
- Asignar/reasignar responsable de atención de una solicitud (`PUT /solicitudes/{id}`, Fase
  1.18) → tipo `SOLICITUD_ASIGNADA`.
- Asignar responsable de un "por hacer" (`POST /tareas/{id}/por-hacer`) → tipo
  `POR_HACER_ASIGNADO`.
- Menciones en comentarios (`POST /tareas/{id}/comentarios`): parseo por regex `@(\w+)` contra
  `miembros_equipo.usuario` (solo activos) → tipo `MENCION_COMENTARIO`; `@todos` reparte a
  todo el equipo con acceso activo (confirmado con el usuario), excluyendo siempre a quien
  escribió el comentario.
- Se expuso `usuario` en `GET /api/miembros-equipo` (antes solo nombre/correo) — lo necesita el
  picker de menciones del frontend para insertar el token correcto.

Frontend: `NotificacionesBell.jsx` en la esquina superior derecha del header (junto a
`ThemeToggle`), con badge rojo del conteo (poll cada 30s, sin librería nueva — no hay
websockets en el proyecto), panel desplegable con las notificaciones recientes (clic navega a
la solicitud/tarea y la marca leída) y "Marcar todas como leídas". `ComentarioFormulario.jsx`
gana un picker ligero de menciones (al escribir `@` filtra `fetchMiembrosEquipo()` + una entrada
sintética "todos") — es solo una ayuda de UI, el backend reconoce `@usuario`/`@todos` igual si
se escribe a mano.

166 tests de backend en verde (13 nuevos). Verificado por `curl` contra la BD real con sesión de
Scrum Master y de Team (`DOVELA_WA`): asignar una tarea a otro miembro genera su notificación;
`@todos` en un comentario notificó exactamente a los 2 miembros activos distintos del autor (de
12 miembros solo 3 tienen acceso activo hoy); `@DOVELA_WA` notificó solo a ese miembro; marcar
una notificación propia funciona, marcar todas funciona, e intentar marcar una notificación ajena
devuelve 404 (protegido por `destinatario_id` en el `WHERE`). Datos y notificaciones de prueba
borrados de la BD real al terminar. Reconstruidos y reiniciados los contenedores `api`/`frontend`
locales con este código. **Falta la pasada visual del usuario** (junto con las de las Fases
1.17-1.19).

**2026-09-02 — Fase 1.19, filtros por defecto "mis tareas"/"mis solicitudes" (tercera de 5
sub-fases del plan `/home/lg/.claude/plans/nifty-wishing-hopper.md`):** el Tablero ya tenía un
filtro de responsable (`<select>` con "Todos los responsables"), pero arrancaba siempre en
"Todos" — ahora `TableroPage` recibe `usuarioActual` (nuevo, antes no lo recibía en
`App.jsx`) y preselecciona su propio id, sin quitar la opción de cambiarlo. Para Solicitudes no
existía ningún filtro de involucramiento: nuevo parámetro `involucrado_id` en
`GET /api/solicitudes` (`repository.list_solicitudes`) que filtra por `solicitante =
involucrado_id OR responsable_atencion_id = involucrado_id OR EXISTS tarea con responsable_id =
involucrado_id` — cubre los 3 roles en los que alguien puede estar involucrado en una solicitud.
Nuevo selector "Ver: Mis solicitudes / Todas" en `SolicitudesPage` (ahora también recibe
`usuarioActual`), default "Mis solicitudes". 153 tests de backend en verde (1 nuevo); verificado
por `curl` contra la BD real con sesión de Scrum Master: sin filtro trae 47 solicitudes, con
`involucrado_id` del propio usuario trae 17 (mezcla de solicitudes propias como solicitante y
ajenas donde es responsable de alguna tarea, confirmando que las 3 condiciones del OR
funcionan). Reconstruidos y reiniciados los contenedores `api`/`frontend` locales con este
código. **Falta la pasada visual del usuario** (junto con las de las Fases 1.17 y 1.18).

**2026-09-02 — Fase 1.18, fecha de entrega + responsable de atención + semáforo de
vencimiento (segunda de 5 sub-fases del plan `/home/lg/.claude/plans/nifty-wishing-hopper.md`):**
`solicitudes` no tenía fecha de entrega ni un responsable de *atenderla* (distinto del
`solicitante`, que es quien la pidió). Se agregaron `fecha_entrega` (date) y
`responsable_atencion_id` (FK a `miembros_equipo`) vía
`backend/sql/012_fecha_entrega_responsable_solicitud.sql` (corrida contra la BD real). Ambos
campos son obligatorios (validados en `SolicitudUpdate`, mismo criterio que ya usaba
`fecha_completado`, no un constraint de BD) desde que el estatus llega a "Planeado" (y se
mantienen obligatorios en "En progreso"/"Completado"); en "En espera"/"Cancelado" siguen siendo
opcionales. El formulario de editar solicitud extiende la lógica condicional que ya existía para
"Fecha Completado" y muestra/exige los dos campos nuevos al elegir esos estatus. Las tareas
heredan y muestran `solicitud_fecha_entrega` (mismo JOIN que ya traía `solicitud_prioridad` de la
Fase 1.17). Nuevo semáforo de vencimiento (`frontend/src/utils/vencimiento.js` +
`VencimientoBadge.jsx`, distinto del semáforo de prioridad): verde (>7 días, misma ventana que ya
usa el Monitor para "por vencer"), amarillo (≤7 días), rojo (vencida) — se apaga en estatus
terminales (Completado/Cancelado, evaluado por tarea, no por la solicitud completa). Badges
visibles en `SolicitudDetallePage`, `SolicitudCard`, `TareaItem`, `TareaDetallePage` y las
tarjetas del Tablero. 152 tests de backend en verde (3 nuevos); verificado por `curl` contra la
BD real con sesión de Scrum Master: rechazo 422 al pasar a Planeado/En progreso/Completado sin
ambos campos, aceptación con ambos, y herencia confirmada en la tarea recién creada. Datos de
prueba limpiados de la BD real al terminar (solicitud y tarea de prueba borradas). Reconstruidos
y reiniciados los contenedores `api`/`frontend` locales con este código. **Falta la pasada visual
del usuario** (junto con la de la Fase 1.17, pendiente también).

**2026-09-02 — Fase 1.17, semáforo de prioridad heredado en tareas (primera de 5 sub-fases del
flujo Solicitud-Tarea pedido por el usuario; ver plan completo en
`/home/lg/.claude/plans/nifty-wishing-hopper.md`):** `solicitudes.orden_prioridad` era
`varchar(100)` de texto libre sin validar; se migró (`backend/sql/011_orden_prioridad_entero.sql`,
corrida contra la BD real) a entero validado 1-5 con default 3 (Media), según
`00_ARCHIVOS/matriz_prioridades_scrum.md` (1=Crítica...5=Trivial, colores fijos de la matriz, no
un catálogo en BD). Las tareas ahora heredan y muestran la prioridad de su solicitud padre
(`solicitud_prioridad` en `TareaOut`, vía el mismo JOIN que ya traía `cliente` heredado) — de
solo lectura, sin duplicar la columna en `tareas`. Formularios de crear/editar solicitud pasan de
un `<input type="number">` libre a un `<select>` de 5 niveles. Nuevo componente
`PrioridadBadge.jsx` reutilizado en `SolicitudDetallePage`, `SolicitudCard`, `TareaItem`,
`TareaDetallePage` y las tarjetas del Tablero. 149 tests de backend en verde (3 nuevos);
verificado por `curl` contra la BD real con sesión de Scrum Master: rechazo 422 con
`orden_prioridad` fuera de 1-5, default 3 si se omite, herencia correcta confirmada en
`GET /api/solicitudes/{id}/tareas` y `GET /api/tareas` (Tablero). Reconstruidos y reiniciados los
contenedores `api`/`frontend` locales con este código. **Falta la pasada visual (claro/oscuro)
del usuario** — la extensión de Chrome no estaba conectada en esta sesión.

**2026-09-01 — Fase 1.16, subvistas de detalle por métrica en Dirección General:** para las 3
métricas de conteo de solicitudes del tablero (en proceso, concluidas, nuevas — tareas y horas
quedan igual, son agregados), el usuario pidió una subvista con mosaico + gráfica de pie por
cliente + gráfica de pie por área + tabla de solicitudes individuales (Nombre, Cliente, Fecha
de solicitud, Solicitante), abierta con clic en el tile correspondiente y un botón "Volver".
Nuevo endpoint `GET /api/direccion-general/detalle-solicitudes?metrica=&desde=&hasta=` (mismo
guard de rol), nuevo componente `PieChart.jsx` reutilizable en SVG puro (sin librería nueva) y
`DireccionGeneralDetalleMetrica.jsx`. Con 15 clientes y 9 áreas reales en la BD, cada pie se
limita a top 5 + "Otros" (máx. 6 rebanadas), con paleta de 5 colores categóricos validada con el
skill `dataviz` (`validate_palette.js`, PASS claro/oscuro) — "Otros" en gris neutro, no
validado como color de serie. 146 tests de backend en verde (7 nuevos); verificado por `curl`
contra la BD real con sesión de Product Owner: el conteo de solicitudes de las 3 métricas
(29/17/47 para 2026-08-01/31) coincide exacto con los totales del endpoint de KPIs ya
existente. Falta la pasada visual en navegador y el deploy a TEST. Detalle completo en
`00_ARCHIVOS/BITACORAS/2026-09-01.md` y el plan
`/home/lg/.claude/plans/calm-beaming-muffin.md`.

**2026-08-31 — Fase 1.15, Tablero de Dirección General:** el usuario pidió una vista de solo
lectura, minimalista, para presentar el avance del área a dirección general — separada del
Monitor existente (operativo, para Scrum Master/Product Owner). Muestra 7 KPIs (solicitudes y
tareas en proceso, concluidas en un rango de fechas elegible, nuevas en el rango, y horas
estimadas del rango) desglosados por Cliente, Tipo de solicitud, Área (`miembros_equipo.perfil`
— columna que ya existía en la BD real y ya estaba poblada, no hizo falta ninguna migración) y
Estatus. Nuevo endpoint `GET /api/direccion-general/kpis?desde=...&hasta=...` (mismo guard de
rol que el Monitor, `require_scrum_master_or_product_owner`), nueva página
`DireccionGeneralPage.jsx` (ruta `/direccion-general`), todo con tablas HTML simples (sin
gráficas nuevas). 139 tests de backend en verde (6 nuevos); verificado por `curl` contra la BD
real con los 3 roles de prueba, números contrastados exactamente contra SQL directo. Detalle
completo, incluida una nota de diseño explícita sobre qué significa "área" para solicitudes vs.
tareas, en `00_ARCHIVOS/BITACORAS/2026-08-31.md` y el plan
`/home/lg/.claude/plans/compressed-dreaming-sunset.md`. **2026-09-01:** verificado en navegador
por el usuario y desplegado en TEST (ver `00_ARCHIVOS/BITACORAS/2026-09-01.md`).

**2026-08-27 — Fase 1.14, portal bajo el subpath /dovela_control:** infraestructura pidió que
el portal responda bajo `/dovela_control` (para ponerlo detrás de un dominio/reverse-proxy
compartido más adelante), con la API accesible por el mismo host/puerto que el frontend (no en
su propio origen como hasta ahora) y la raíz (`/`) funcionando en paralelo con la misma app. El
nginx del contenedor `frontend` pasó a ser el único punto de entrada: sirve la SPA bajo
`/dovela_control` (y en `/`, mismo build) y hace de reverse proxy de `/dovela_control/api/*`
hacia el contenedor `api` interno — sin CORS de por medio para el navegador. El puerto directo
de la API (8000 local, 8005 TEST) sigue publicado sin cambios, en paralelo. Ver detalle completo
de los hallazgos no obvios (reescritura de rutas de Vite, `new URL()` sin base en `api.js`,
separación de `FRONTEND_ORIGIN`/`FRONTEND_BASE_PATH`, `client_max_body_size`, y un 403 propio de
nginx encontrado y corregido en la sesión) en `00_ARCHIVOS/BITACORAS/2026-08-27.md` y el plan
`/home/lg/.claude/plans/stateful-stirring-oasis.md`. Desplegado y verificado por `curl` y en
navegador tanto local como en TEST (`t_apex`, `/u01/docker_containers/portal_seguimiento`) —
recuperación de contraseña de punta a punta con el link ya apuntando al subpath nuevo, login,
navegación, F5 en ruta profunda, y carga de un adjunto de ~9 MB a través del proxy nuevo.

**Mismo día, seguimiento — fix de mixed content:** al publicarlo en un dominio HTTPS real
(`https://apps.stofactura.com/dovela_control/`, reverse proxy externo de infraestructura) el
login falló por "mixed content" — `config.js` traía grabado el origen HTTP interno de TEST, que
el navegador bloqueó desde una página HTTPS. Se reemplazó ese mecanismo (grababa un valor fijo
por ambiente) por un cálculo en runtime en `frontend/src/api.js`
(`` `${window.location.origin}/dovela_control` ``), que funciona automáticamente para cualquier
dominio/IP/protocolo sin configuración por ambiente — se borraron `public/config.js` y
`docker-entrypoint.sh`, ya no hacen falta. Verificado con login real por `curl` y en navegador
contra local, TEST, y el dominio público. Commit `90d51dc`.

**2026-08-27 — Fase 1.13, reglas de permisos más finas por rol:** hasta ahora solo había 2
reglas de rol reales (crear tarea y gestión de usuarios, ambas Scrum Master); todo lo demás
—editar/borrar solicitudes y tareas, crear/editar/borrar hitos/comentarios/"por hacer"— estaba
abierto a cualquier usuario logueado. Definido con el usuario: **borrar solicitud/tarea pasa a
ser exclusivo del Scrum Master** (el resto del equipo usa el nuevo estatus "Cancelado" en vez
de borrar); **editar/borrar comentarios, hitos e ítems "por hacer" pasa a ser solo del autor o
del Scrum Master** (moderación). Editar solicitud/tarea sigue abierto a todos; crear también
(salvo tareas, que ya era solo Scrum Master desde la Fase 1.7). Enlaces de tarea quedaron fuera
de alcance (no tienen endpoint de editar/borrar todavía). Se agregó el estatus "Cancelado" al
catálogo `estatus_tarea` (no existía, a diferencia del catálogo de solicitudes) vía
`backend/sql/010_cancelado_tarea.sql`, y se corrigieron las 3 queries del Monitor que
consideraban "no completada" como sinónimo de "activa" (una tarea cancelada ya no cuenta como
vencida ni infla la carga de un responsable). 134 tests de backend en verde (11 nuevos).
Verificado exhaustivamente contra la API real con los 3 roles de prueba y visualmente en
navegador. Detalle completo en `00_ARCHIVOS/BITACORAS/2026-08-27.md` y plan
`/home/lg/.claude/plans/stateful-stirring-oasis.md`.

**2026-08-26 — Fase 1.12, Monitor de tareas:** quedaba anotada "sin diseñar" en el roadmap.
Se definieron con el usuario los cuatro indicadores (tareas vencidas/por vencer, carga por
responsable, cumplimiento planeado vs. real, distribución por estatus), el acceso (solo
Scrum Master y Product Owner) y la ubicación (página nueva `/monitor` en el sidebar).

- **Sin precedente en el repo**: no existía ninguna función de agregación (`COUNT`/`GROUP
  BY`) en `repository.py`, ninguna dependency de auth para "más de un rol" (se agregó
  `require_scrum_master_or_product_owner`), ni ninguna librería de gráficas instalada. Se
  construyó con CSS plano (sin nueva dependencia de npm) reusando el sistema de tokens de
  color ya establecido — las barras de "Distribución por estatus" reusan los mismos hues
  que ya identifican cada estatus en Tablero/detalle de tarea (aunque en un tono más
  saturado que el pastel de las insignias, necesario para que el relleno de la barra no se
  pierda contra el fondo — mismo hue, distinto paso de la rampa). Se agregó un token nuevo
  `--warning-bg`/`--warning-text` (no existía) para "por vencer".
- Pequeño refactor habilitador: `CLASE_POR_ESTATUS` estaba duplicado en `TareaItem.jsx` y
  `TareaDetallePage.jsx`; se centralizó en `frontend/src/constants/estatusTarea.js` (que
  también exporta `RELLENO_POR_ESTATUS`, el mapeo de colores saturados para barras) para no
  agregar una tercera copia.
- Cada indicador de "vencidas"/"por vencer" es una tabla real (no solo un conteo), con
  enlace directo a cada tarea — el punto es poder actuar, no solo ver un número.
- 4 tests nuevos (`test_api_monitor.py`), 123 tests de backend en verde. Verificado
  end-to-end en navegador en modo claro y oscuro: números del monitor contrastados contra
  consultas directas a la BD real (coinciden exactamente); un usuario Team no ve "Monitor"
  en el sidebar y recibe 403 tanto navegando a `/monitor` por URL directa (redirige a `/`)
  como pegándole al endpoint `/api/monitor/kpis` directamente con su token. Nota curiosa
  de la verificación: los conteos de "vencidas"/"por vencer" cambiaron en vivo entre dos
  chequeos (23→24 y 4→3) porque pasó suficiente tiempo real como para cruzar la medianoche
  — confirma que el cálculo por fecha es dinámico, no un bug.

**2026-08-26 — Fase 1.11, checklist "Por hacer" en tareas:** la tabla
`solicitudes.tarea_por_hacer` ya existía en la BD real (esquema heredado, sin migración
versionada del repo) pero no tenía backend ni frontend. Se agregó CRUD completo como nueva
pestaña "Por hacer" en el detalle de tarea:

- Backend: `GET`/`POST /api/tareas/{id}/por-hacer` (colección) y `PUT`/`DELETE
  /api/tarea-por-hacer/{id}` (rutas planas, igual patrón que comentarios). `esta_completa`
  se guarda como `'Y'`/`'N'` en la columna real (única convención documentada en el repo,
  `004_estatus_tarea.sql`) pero se traduce a `bool` en `repository.py` — el schema y el
  frontend nunca ven el detalle de almacenamiento.
- Borrado físico real (`DELETE FROM`, no borrado lógico) — la tabla no tiene
  `borrado_en`/`borrado_por`, mismo criterio ya usado en `enlaces_tarea` (documentado en el
  docstring de `delete_tarea`).
- **Hallazgo durante la verificación**: el docstring de `delete_tarea` decía que
  `enlaces_tarea`/`tarea_por_hacer` "se borran físicos solos vía ON DELETE CASCADE" al borrar
  la tarea/solicitud padre — pero `delete_tarea`/`delete_solicitud` hacen **borrado lógico**
  (`UPDATE borrado_en`, nunca `DELETE FROM`), así que ese `ON DELETE CASCADE` en realidad
  **nunca se dispara** por el flujo normal de la app. Verificado en la BD real: al borrar una
  solicitud/tarea de prueba, la fila de `tarea_por_hacer` quedó huérfana (no se borró sola).
  Este comportamiento ya era así de antes para `enlaces_tarea` (mismo diseño de FK) — no es
  una regresión de esta fase, solo quedó documentado con precisión ahora. No se tocó código
  para "corregirlo" (cambiaría el comportamiento ya existente de `enlaces_tarea` también,
  fuera de alcance de esta fase).
- Toggle rápido de completado (checkbox inline) reutiliza el mismo `PUT` de edición completa,
  con actualización optimista en el frontend (sin recargar todo el detalle de la tarea).
- 6 tests nuevos (`test_api_tareas.py` + nuevo `test_api_tarea_por_hacer.py`), 119 tests de
  backend en verde. Verificado end-to-end en navegador: crear ítem, toggle de completado con
  persistencia confirmada tras F5 (mapeo `'Y'/'N'` ↔ `bool` correcto), edición preservando
  `esta_completa`, borrado individual, y el hallazgo de la cascada arriba. Datos de prueba
  limpiados de la BD real al terminar (solicitud/tarea/ítem físicamente borrados).

**2026-08-26 — Fase 1.10, módulo de gestión de usuarios:** hasta ahora `miembros_equipo`
solo se poblaba por seed externo; la página Usuarios solo permitía otorgar/editar *acceso*
(rol + contraseña) a un miembro que ya existía como fila. Se agregó el CRUD completo:

- **Alta en dos pasos** (decisión de diseño ya acordada): `POST /api/usuarios` crea solo la
  identidad (usuario, nombre, correo) con `acceso_activo=false`; el flujo ya existente
  "Otorgar acceso" se reusa sin cambios para el segundo paso (rol + contraseña).
- **Baja lógica real**: nuevas columnas `borrado_en`/`borrado_por` en `miembros_equipo`
  (migración `backend/sql/009_baja_logica_miembros.sql`, corrida contra la BD real), mismo
  patrón que `solicitudes`/`tareas`/`comentarios`/`hitos`. `DELETE /api/usuarios/{id}` oculta
  al miembro de `list_miembros`/`list_miembros_con_acceso` (selects de solicitante/
  responsable y página Usuarios) y le revoca el acceso — pero **no** toca ningún JOIN
  histórico: una solicitud/tarea ya atribuida a un miembro dado de baja sigue mostrando su
  nombre con normalidad (verificado creando un miembro de prueba, asignándolo como
  solicitante de una solicitud, dándolo de baja, y confirmando que la solicitud siguió
  mostrando su nombre).
- **Actualización unificada**: `PUT /api/usuarios/{id}` reemplaza el viejo
  `PUT /{id}/acceso` — edita identidad y acceso (rol/activo/contraseña) en un solo formulario
  (`EditarUsuarioFormulario.jsx`), reemplazando el uso de `AccesoFormulario` para edición
  (que ahora solo cubre "otorgar acceso" la primera vez).
- Nuevos índices únicos parciales (case-insensitive, solo entre miembros activos) en
  `usuario`/`correo_electronico` — antes no había ningún constraint de unicidad; un
  `usuario`/correo dado de baja puede reutilizarse en una alta nueva.
- 9 tests nuevos en `backend/tests/test_api_usuarios.py` (23 en total en ese archivo), 112
  tests de backend en verde. Verificado end-to-end en navegador: alta con 409 por duplicado,
  otorgar acceso, edición unificada, aparición/desaparición en selectores de solicitante, baja
  lógica, y persistencia del nombre en histórico. Datos de prueba limpiados de la BD real al
  terminar (borrado físico, sin asociaciones reales). Detalle completo en
  `00_ARCHIVOS/BITACORAS/2026-08-26.md` y plan `/home/lg/.claude/plans/sleepy-exploring-octopus.md`.

**Cambio de alcance (2026-08-26):** se quitaron del roadmap las Fases 1.3 (Conexión ERP
Oracle), 1.4 (API pública de Solicitudes), 1.5 (Ingesta de archivos) y 2 (Actualización de
tareas, ya cubierta en la práctica por el CRUD de tareas de la Fase 1.7) — dejaron de ser
prioridad. Se agregaron tres fases nuevas a pedido del usuario:

- **Fase 1.10 — Módulo de gestión de usuarios:** hoy `UsuariosPage.jsx` solo permite
  otorgar/editar el *acceso* (rol Scrum + contraseña) de miembros que ya existen como fila en
  `miembros_equipo` — no hay alta de un miembro nuevo, ni baja (eliminar/desactivar al miembro
  como persona, distinto de solo quitarle acceso de login), ni edición de sus datos propios
  (nombre, correo). Falta diseñar e implementar el CRUD completo.
- **Fase 1.11 — "Por hacer" en tareas:** la tabla `solicitudes.tarea_por_hacer` ya existe en
  la base de datos real (`solicitud_id`, `tarea_id`, `responsable_id`, `nombre`, `descripcion`,
  `esta_completa`, auditoría `creado_por`/`actualizado_por`) — viene del esquema original que
  ya estaba poblado, pero hoy solo se menciona en un comentario de `repository.py` sobre
  borrado en cascada; no tiene backend (endpoints) ni frontend. Es una lista de subtareas o
  checklist asociada directamente a una tarea (`tareas`), no a la solicitud.
- **Fase 1.12 — Monitor de tareas:** panel de indicadores clave (KPIs) para Scrum Master y
  Product Owner, distinto del Tablero (kanban) que ya existe. Sin diseño todavía — falta
  definir con el usuario qué indicadores exactamente (¿tareas vencidas, carga por responsable,
  tiempo promedio de ciclo, cumplimiento de fechas planeadas vs. reales?).

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
las tome nota):** `DOVELA_LG` (Scrum Master) → `DovelaScrum2026!` (⚠️ el usuario la cambió
en algún momento antes del 2026-08-26 a `Latitude123$` — ver
`00_ARCHIVOS/BITACORAS/2026-08-26.md`). También se otorgó
acceso de prueba a `DOVELA_WA` (Team) → `ClaveInicial2026!` (confirmada vigente el
2026-08-26) y `DOVELA_JC` (Product Owner) → `ClaveJC2026!` — el resto de los 12 miembros del
equipo siguen sin acceso (`acceso_activo=false`) hasta que el Scrum Master se los otorgue
desde la página
"Usuarios".

**2026-08-25 — Migración de navegación por estado a rutas reales (✅ implementado y
verificado end-to-end en navegador el 2026-08-26):** el frontend era efectivamente una
landing page de una sola pantalla (`App.jsx` con un `useState("pagina")` decidiendo qué
renderizar, sin URLs reales, sin F5 funcional, sin poder compartir un link directo). Se
migró a `react-router-dom` con rutas reales (`/`, `/chat`, `/solicitudes`, `/solicitudes/:id`,
`/tablero`, `/tareas/:id`, `/usuarios`, `/cambiar-password`). `npm run build` en verde y el
fallback SPA de `nginx.conf` (`try_files ... /index.html`, ya existía, no se tocó) confirmado
por `curl` sirviendo rutas profundas con `200`. Verificación visual completa en navegador
(checklist de `00_ARCHIVOS/BITACORAS/2026-08-25.md`, ejecutada el 2026-08-26): navegación por
sidebar cambia la URL en cada opción; `/solicitudes/<id>` sobrevive a F5; desde una tarea
(abierta tanto desde una solicitud como desde el Tablero) "Regresar" navega a la solicitud
padre; "Cambiar contraseña" → `/cambiar-password` y cancelar vuelve a `/`; cerrar sesión
vuelve a `/` sin sidebar; el flujo de recuperación de contraseña por correo (`?reset_token=`)
se probó de punta a punta con `DOVELA_WA` leyendo el link real del mailserver de pruebas por
IMAP; un usuario sin rol Scrum Master (`DOVELA_WA`, rol Team) no puede llegar a `/usuarios`
por URL directa (redirige a `/`). Sin hallazgos — no hizo falta ningún cambio de código.
Detalle completo, plan y decisiones de diseño en `00_ARCHIVOS/BITACORAS/2026-08-25.md` y
`/home/lg/.claude/plans/quirky-watching-boole.md`.

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
    `GET /api/canales-solicitud`, `GET /api/estatus`). También expone comentarios/hitos/
    enlaces de tarea con el nombre de autor resuelto (`creado_por_nombre`):
    `GET/POST /api/tareas/{id}/enlaces` y `GET /api/solicitudes/{id}/comentarios|hitos|enlaces`
    (agregados de solo lectura, para ver todo lo de una solicitud sin entrar tarea por tarea).
    `GET /api/solicitudes/{id}/adjuntos` y `.../adjuntos/{adjunto_id}/descargar` permiten listar
    y descargar los archivos ya guardados de una solicitud. Las tareas ya distinguen fechas
    planeadas (`fecha_inicio`/`fecha_fin`, existentes) de fechas reales (`fecha_inicio_real`/
    `fecha_fin_real`, nuevas y nullable) en `POST /api/solicitudes/{id}/tareas` y
    `PUT /api/tareas/{id}`.
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
- **Tests**: 105 tests unitarios en `backend/tests/` (parser, client_matcher,
  title_synthesizer, auth, endpoints de solicitudes incl. adjuntos/formulario/orden_por/
  descarga, comentarios/hitos/enlaces de tarea, endpoints de catálogos) — todos pasan. Frontend
  solo verificado con `npm run build` (sin tests
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

**⭐ Verificar e2e con curl/navegador los 2 ajustes del 2026-09-03** (auto-notificación y permiso
de creación de tareas para el responsable de atención) contra la BD real — hoy solo están
verificados por los 180 tests de backend (mocks de repositorio), no se hizo la pasada con curl
contra la BD real por no tener credenciales de prueba a mano en esa sesión.

**⭐ Desplegar a TEST las Fases 1.16 a 1.21.** Las 6 sub-fases (subvistas de Dirección General +
las 5 del flujo Solicitud-Tarea) ya están implementadas y **verificadas visualmente por el
usuario** (2026-09-03); falta el deploy (mismo procedimiento que la Fase 1.15: push,
`git stash`/`pull`/`stash pop` en `t_apex`, rebuild de `api`/`backend`/`frontend`).

0. **⭐ Verificar en navegador la migración a rutas reales (2026-08-25).** El código ya está
   escrito y el build pasa, pero falta el recorrido visual completo (navegar por el sidebar,
   refrescar F5 en `/solicitudes/:id` y `/tareas/:id`, recuperación de contraseña, guard de
   `/usuarios`). Checklist completo en `00_ARCHIVOS/BITACORAS/2026-08-25.md`.
1. **⭐ Otorgar acceso al resto del equipo.** Solo `DOVELA_LG` (Scrum Master), `DOVELA_WA`
   (Team, contraseña de prueba) y `DOVELA_JC` (Product Owner, contraseña de prueba) tienen
   acceso activo hoy. Los otros 9 miembros siguen con `acceso_activo=false`. `DOVELA_LG`
   puede otorgárselo desde la página "Usuarios" del portal. Ver también la nota de
   contraseñas de prueba más abajo — conviene cambiarlas o rotarlas.
2. ~~Confirmar con el usuario si la única regla de permisos actual... es suficiente~~ —
   **resuelto en la Fase 1.13** (2026-08-27): borrar solicitud/tarea ahora es solo Scrum
   Master; editar/borrar comentarios, hitos y "por hacer" ahora es solo del autor o Scrum
   Master. Pendiente futuro si surge: reglas de rol para hitos/comentarios/enlaces a nivel de
   solicitud (hoy esas acciones agregadas de solo lectura en `SolicitudDetallePage` no tienen
   botones de editar/borrar, así que no aplicó gating ahí), y construir editar/borrar de
   enlaces de tarea si algún día se necesita (hoy no existe esa funcionalidad en absoluto).
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

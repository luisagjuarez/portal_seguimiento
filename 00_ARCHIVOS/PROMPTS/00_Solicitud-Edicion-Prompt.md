# Prompt: Implementación de Vista Maestro-Detalle, Edición/Borrado de Solicitudes y CRUD de Tareas

## Contexto del Proyecto

Estás trabajando en el **Portal de Seguimiento DOVELA**, un sistema para gestionar requerimientos de software y tareas internas de los equipos de tecnología. 

### Stack Tecnológico:
*   **Backend:** Python 3.12+ con FastAPI.
*   **Base de Datos:** PostgreSQL (base `dovela_control`, esquema `solicitudes`), usando un pool de conexiones gestionado por `psycopg` (v3). Las consultas deben respetar que el esquema ya está definido con catálogos y llaves foráneas reales.
*   **Frontend:** Single Page Application (SPA) desarrollada con React y Vite. La navegación se realiza a través de un estado simple en `App.jsx` (sin librerías de routing complejas como `react-router`).
*   **Estilos:** CSS Vanilla (los estilos se agregan a `frontend/src/styles.css`). No se utiliza TailwindCSS.

---

## 1. Estructura de la Base de Datos (PostgreSQL)

Debes trabajar con las siguientes tablas del esquema `solicitudes`:

### Tabla: `solicitudes`
*   `id` (bigint, llave primaria)
*   `nombre` (character varying, NOT NULL) — Título de la solicitud.
*   `descripcion` (character varying, NULL)
*   `solicitante` (bigint, NULL, FK a `miembros_equipo.id`)
*   `cliente` (bigint, NULL, FK a `clientes.id`)
*   `tipo` (bigint, NULL, FK a `tipos_solicitud.id`)
*   `codigo_estatus` (character varying, NOT NULL, FK a `estatus.codigo`) — Por defecto nace en `'EN ESPERA'`.
*   `orden_prioridad` (character varying, NULL)
*   `canal` (bigint, NULL, FK a `canales_solicitud.id`)
*   `creado_en` (timestamp with time zone, NOT NULL)
*   `creado_por` (character varying, NOT NULL)
*   `actualizado_en` (timestamp with time zone, NOT NULL)
*   `actualizado_por` (character varying, NOT NULL)

### Tabla: `tareas`
*   `id` (bigint, llave primaria)
*   `solicitud_id` (bigint, NOT NULL, FK a `solicitudes.id` con `ON DELETE CASCADE`)
*   `hito_id` (bigint, NULL, FK a `hitos.id`)
*   `responsable_id` (bigint, NULL, FK a `miembros_equipo.id`)
*   `nombre` (character varying, NOT NULL) — Título de la tarea.
*   `descripcion` (character varying, NULL)
*   `fecha_inicio` (date, NOT NULL) — *Nota: al insertar una tarea nueva por defecto, inicializarla con la fecha actual (now().date()).*
*   `fecha_fin` (date, NOT NULL) — *Nota: al insertar una tarea nueva, inicializarla por defecto con la fecha actual o fecha actual + 7 días.*
*   `esta_completa` (character varying, NULL) — Almacena `'Y'` (Completada) o `'N'` (Pendiente).
*   `horas_estimadas` (integer, NULL)
*   `horas_reales` (integer, NULL)
*   `creado_en` (timestamp with time zone, NOT NULL) — Autocompletar con `now()`.
*   `creado_por` (character varying, NOT NULL) — Autocompletar con `current_user` o el usuario activo.
*   `actualizado_en` (timestamp with time zone, NOT NULL) — Autocompletar con `now()`.
*   `actualizado_por` (character varying, NOT NULL) — Autocompletar con `current_user` o el usuario activo.

---

## 2. Requerimientos Funcionales a Implementar

### A. Vista Detalle de la Solicitud (Maestro-Detalle)
1.  **Navegación:** Al hacer clic en una tarjeta de solicitud (`SolicitudCard.jsx`) en la página de Solicitudes, se debe cambiar la vista en `App.jsx` (`pagina` = `"solicitud-detalle"`) y mostrar la página de detalles pasando el `solicitudId`.
2.  **Visualización:** Esta página debe cargar los detalles completos de la solicitud mediante una petición al backend, y listar todas las tareas asociadas a la misma. Debe presentar:
    *   Información general: Título, Cliente, Tipo de Solicitud, Solicitante, Estatus y Fecha de Creación.
    *   Sección de **Tareas**: Un listado de las tareas asociadas a esta solicitud.
    *   Botones de acción principales: **Editar Solicitud**, **Borrar Solicitud** y **Regresar** (para volver a la lista de solicitudes).

### B. Edición y Borrado de Solicitudes
1.  **Editar Solicitud:**
    *   Al hacer clic en "Editar Solicitud", se debe abrir un formulario (puede ser en un modal o en la misma página) precargado con los datos actuales: Título, Descripción, Cliente (utilizando el autocomplete existente), Tipo de Solicitud y Estatus.
    *   Se debe poder actualizar el estatus de la solicitud (cargando las opciones desde el catálogo `/api/estatus`).
    *   Al guardar, se realiza un `PUT` o `PATCH` al backend. Las columnas de auditoría `actualizado_en` y `actualizado_por` deben actualizarse de forma explícitamente en la base de datos.
2.  **Borrar Solicitud:**
    *   Al hacer clic en "Borrar Solicitud", se debe abrir un modal pidiendo confirmación.
    *   Si se confirma, se realiza un `DELETE` al backend.
    *   Al eliminarse con éxito, el sistema debe redirigir al usuario de regreso a la lista de solicitudes (`"solicitudes"`).
    *   *Nota técnica:* Las tareas y comentarios relacionados se eliminan en cascada en la base de datos debido a las restricciones de clave foránea existentes.

### C. Gestión de Tareas (CRUD de Tareas)
Desde la vista detallada de la solicitud se debe poder realizar la gestión de tareas:
1.  **Agregar Tarea:**
    *   Botón "Agregar Tarea" que abre un formulario.
    *   Campos del formulario:
        *   **Título** (obligatorio).
        *   **Descripción** (opcional).
        *   **Responsable** (selector que muestra la lista de miembros del equipo obtenidos de `/api/miembros-equipo`).
        *   **Estado** (Selector entre "Pendiente" (`'N'`) y "Completado" (`'Y'`), por defecto "Pendiente").
    *   Las fechas de creación y modificación se mostrarán como texto informativo si corresponde, pero se inicializan en el backend.
    *   Al guardar, la tarea se inserta en la base de datos y se recarga la lista de tareas en pantalla.
2.  **Editar Tarea:**
    *   Botón de edición en cada elemento de la lista de tareas.
    *   Abre el mismo formulario precargado con la información actual de la tarea.
    *   Permite modificar el Título, Descripción, Responsable y Estado.
    *   Al guardar, actualiza el registro en el backend y refresca la lista.
3.  **Borrar Tarea:**
    *   Botón de eliminación en cada elemento de la lista de tareas.
    *   Debe abrir un **modal de confirmación** para el borrado.
    *   Si se confirma, se llama al endpoint de eliminación en el backend.
    *   Si se cancela, se cierra el modal y se permanece en la vista de detalle.

---

## 3. Guía de Modificación del Código

Debes implementar la funcionalidad realizando cambios en los siguientes archivos y siguiendo las directrices del proyecto:

### backend/app/db/repository.py
1.  Implementar `get_solicitud_by_id(cursor, solicitud_id: int) -> dict | None`: obtener los detalles de una solicitud específica incluyendo joins para traer textos legibles de cliente, tipo, estatus y solicitante.
2.  Implementar `update_solicitud(cursor, solicitud_id: int, nombre: str, descripcion: str, cliente_id: int | None, tipo_id: int | None, codigo_estatus: str) -> None`: actualizar la solicitud modificando explícitamente `actualizado_en = now()` y `actualizado_por = current_user`.
3.  Implementar `delete_solicitud(cursor, solicitud_id: int) -> None`: eliminar la solicitud.
4.  Implementar funciones de tareas:
    *   `list_tareas_by_solicitud(cursor, solicitud_id: int) -> list[dict]`: listar tareas con joins para traer el nombre del responsable de `miembros_equipo`.
    *   `insert_tarea(cursor, solicitud_id: int, nombre: str, descripcion: str, responsable_id: int | None, esta_completa: str) -> int`: insertar una nueva tarea (recuerda que `fecha_inicio` y `fecha_fin` son obligatorios; inicialízalos con la fecha actual si no son provistos).
    *   `update_tarea(cursor, tarea_id: int, nombre: str, descripcion: str, responsable_id: int | None, esta_completa: str) -> None`: actualizar una tarea específica.
    *   `delete_tarea(cursor, tarea_id: int) -> None`: eliminar la tarea por ID.

### backend/app/api/routes_solicitudes.py (u otro módulo de API)
1.  Crear nuevos schemas en `backend/app/api/schemas.py` para peticiones y respuestas:
    *   `SolicitudDetalle`
    *   `SolicitudUpdate`
    *   `TareaOut`
    *   `TareaCreateUpdate`
2.  Definir las rutas FastAPI correspondientes:
    *   `GET /api/solicitudes/{id}`
    *   `PUT /api/solicitudes/{id}`
    *   `DELETE /api/solicitudes/{id}`
    *   `GET /api/solicitudes/{id}/tareas`
    *   `POST /api/solicitudes/{id}/tareas`
    *   `PUT /api/tareas/{id}`
    *   `DELETE /api/tareas/{id}`
3.  Asegura el manejo correcto de transacciones: utiliza `db_conn.commit()` y `db_conn.rollback()` de forma adecuada en los bloques `try-except` de los endpoints de escritura.

### frontend/src/api.js
Añadir las llamadas de red utilizando `fetch`:
*   `fetchSolicitudDetalle(id)`
*   `actualizarSolicitud(id, datos)`
*   `eliminarSolicitud(id)`
*   `fetchTareas(solicitudId)`
*   `crearTarea(solicitudId, datos)`
*   `actualizarTarea(tareaId, datos)`
*   `eliminarTarea(tareaId)`

### frontend/src/App.jsx y componentes frontend
1.  **Navegación:** Modifica el estado en `App.jsx` para admitir una nueva vista `"solicitud-detalle"` y pasa el ID de la solicitud seleccionada.
2.  **SolicitudesPage / SolicitudCard:** Haz que al hacer clic en una `SolicitudCard` se dispare un callback hacia `App.jsx` para cambiar la página a `"solicitud-detalle"` pasando el ID correspondiente.
3.  **Nuevo Componente `SolicitudDetallePage.jsx`:**
    *   Carga y muestra el detalle de la solicitud.
    *   Lista las tareas asociadas.
    *   Implementa botones de editar y eliminar para la solicitud.
    *   Implementa el CRUD de tareas utilizando ventanas modales o formularios desplegables en la misma página.
4.  **Estilos CSS:** Diseña la interfaz en `frontend/src/styles.css` respetando la estética del portal actual (colores del sidebar oscuros, bordes limpios, modales estructurados con `.modal-overlay` y `.modal-content`).

---

## 4. Plan de Verificación

Asegúrate de:
1.  **Tests unitarios:** Escribir y ejecutar pruebas unitarias en `backend/tests/` para verificar los nuevos endpoints de edición/borrado de solicitudes y CRUD de tareas.
2.  **Verificación manual:** Probar la interfaz en el navegador para asegurar que:
    *   La navegación de maestro a detalle es instantánea.
    *   Al guardar los cambios de edición, la información se refresca en base de datos.
    *   El modal de borrado funciona de forma segura.
    *   Las tareas se listan, editan y eliminan limpiamente actualizando la interfaz.

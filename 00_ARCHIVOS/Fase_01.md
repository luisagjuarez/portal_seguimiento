Hola. Vamos a iniciar el desarrollo del "Portal de Seguimiento DOVELA". Es un sistema diseñado para gestionar requerimientos de software y tareas internas de los equipos de tecnología (Fábrica, Soporte, DBAs, Infraestructura).

El stack tecnológico inicial consistirá en:
- Backend: Python (utilizando un framework como FastAPI o Flask, ideal para servicios ligeros, APIs y procesamiento asíncrono).
- Base de datos: Oracle Database (las credenciales y host se definirán por variables de entorno).
- Estructura: Backend y Frontend en directorios separados.
- Despliegue: Docker y Docker Compose para levantar el backend y base de datos local de pruebas.

Quiero comenzar estrictamente con el **Módulo 1.1: Ingestión de Solicitudes por Correo Electrónico**.

### Objetivo de esta tarea:
Desarrollar el servicio backend (o worker) encargado de leer correos electrónicos entrantes y registrar solicitudes automáticamente.

### Instrucciones y Flujo de Trabajo:
1. **Conexión al Correo:** Configurar un listener/polling de correo (IMAP/SMTP o Microsoft Graph/Gmail API) para detectar correos entrantes que contengan "Nueva solicitud" en el asunto.
2. **Procesamiento del Contenido:**
   - **Remitente:** Extraer el email como Solicitante.
   - **Cliente:** Identificar el cliente en el contenido. Buscar en la tabla `Clientes`. Si no existe, insertarlo en la BD.
   - **Campos por Defecto:** Tipo = 'Nuevo', Estatus = 'En espera', Prioridad = NULL.
   - **Descripción:** Extraer el cuerpo del correo, limpiar el formato HTML/texto plano y opcionalmente refinar la redacción (dejando el original como historial).
   - **Título:** Sintetizar el asunto del correo para generar un título claro de la solicitud.
3. **Persistencia en Base de Datos Oracle:**
   - Diseña e implementa el script DDL de creación de tablas necesario para este módulo: `Clientes`, `Solicitudes`, `Adjuntos`, `Solicitudes_Adjuntos`, `Solicitudes_MD`.
   - Asegúrate de usar sentencias SQL compatibles con Oracle DB.
4. **Manejo de Archivos Adjuntos (NFS):**
   - Si el correo incluye adjuntos, guardarlos en un directorio local configurable (que simulará el NFS) y registrar las rutas en la tabla `Adjuntos` y la relación en `Solicitudes_Adjuntos`.
5. **Generación del Archivo de Requerimientos (.md):**
   - Por cada solicitud, crea un archivo `.md` estandarizado que sirva como plantilla de diseño/estimación.
   - Guarda este archivo en el directorio configurado para archivos MD y guarda el registro en la BD.
6. **Dockerización:**
   - Crea el `Dockerfile` para este servicio de backend.
   - Crea un archivo `docker-compose.yml` que levante el Backend y configure las variables de entorno necesarias para la conexión IMAP y Oracle DB.

### Entregables esperados:
- Estructura de directorios organizada (ej. `/backend`).
- Script SQL/DDL compatible con Oracle DB para crear las tablas del Módulo 1.1.
- Código fuente documentado del servicio de lectura, parsing y persistencia de correos.
- Plantilla estándar de documento de requerimientos `.md`.
- `Dockerfile` y `docker-compose.yml` configurados.
- Instrucciones en un archivo `README.md` sobre cómo configurar las credenciales de correo y base de datos para probar localmente.

Por favor, diseña la estructura del proyecto y propón el modelo 
// En Docker, docker-entrypoint.sh sustituye el valor de abajo (no el nombre de la
// propiedad) por la variable de entorno API_BASE_URL al arrancar el contenedor, así
// el mismo build sirve para TEST/PROD sin recompilar.
window.__API_BASE_URL__ = "API_BASE_URL_PLACEHOLDER";

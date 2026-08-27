FROM node:20-slim AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# La imagen base trae su propio index.html (la página de bienvenida de nginx) en la raíz de lo
# que sirve — hay que quitarlo o "shadowea" el fallback de la SPA en location / (nginx lo
# serviría como index de directorio antes de caer al try_files de más abajo).
RUN rm -f /usr/share/nginx/html/index.html
# Vite compila con base "/dovela_control/", así que todas las referencias del bundle (JS, CSS,
# imágenes, config.js) piden esa ruta sin importar por qué URL se cargó la página — el build se
# copia a esa subcarpeta real para que existan físicamente ahí.
COPY --from=build /app/dist /usr/share/nginx/html/dovela_control
COPY nginx.conf /etc/nginx/conf.d/default.conf

# El bundle de Vite ya trae public/config.js copiado a dist/config.js con el placeholder
# literal; se renombra a .template para que el entrypoint lo resuelva en cada arranque
# del contenedor sin necesidad de reconstruir la imagen entre TEST y PRODUCCIÓN.
RUN mv /usr/share/nginx/html/dovela_control/config.js /usr/share/nginx/html/dovela_control/config.js.template

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]

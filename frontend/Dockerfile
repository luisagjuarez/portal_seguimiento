FROM node:20-slim AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# El bundle de Vite ya trae public/config.js copiado a dist/config.js con el placeholder
# literal; se renombra a .template para que el entrypoint lo resuelva en cada arranque
# del contenedor sin necesidad de reconstruir la imagen entre TEST y PRODUCCIÓN.
RUN mv /usr/share/nginx/html/config.js /usr/share/nginx/html/config.js.template

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]

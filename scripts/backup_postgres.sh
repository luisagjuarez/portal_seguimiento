#!/usr/bin/env bash
# Respaldo diario de la base de datos Postgres del Portal DOVELA.
# Pensado para correr por cron en el host donde vive el contenedor de Postgres
# (ej. t_apex), no dentro de un contenedor.
set -euo pipefail

CONTENEDOR="${POSTGRES_CONTAINER:-postgres_db}"
BASE_DATOS="${POSTGRES_DB:-dovela_control}"
USUARIO="${POSTGRES_USER:-dovela_control}"
DESTINO="${BACKUP_DIR:-/u01/RESPALDOS_BD}"
RETENCION_DIAS="${BACKUP_RETENTION_DAYS:-30}"
DOCKER="${DOCKER_CMD:-sudo docker}"

FECHA="$(date +%Y-%m-%d_%H%M%S)"
ARCHIVO="${DESTINO}/${BASE_DATOS}_${FECHA}.sql.gz"

mkdir -p "$DESTINO"

$DOCKER exec "$CONTENEDOR" pg_dump -U "$USUARIO" -d "$BASE_DATOS" | gzip > "$ARCHIVO"

if [ ! -s "$ARCHIVO" ]; then
  echo "ERROR: el respaldo quedó vacío, se borra: $ARCHIVO" >&2
  rm -f "$ARCHIVO"
  exit 1
fi

echo "Respaldo creado: $ARCHIVO ($(du -h "$ARCHIVO" | cut -f1))"

# Retención: borra respaldos de este mismo esquema más viejos que RETENCION_DIAS.
find "$DESTINO" -maxdepth 1 -name "${BASE_DATOS}_*.sql.gz" -mtime "+${RETENCION_DIAS}" -print -delete

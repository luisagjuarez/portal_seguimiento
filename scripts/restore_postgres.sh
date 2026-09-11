#!/usr/bin/env bash
# Restaura un respaldo generado por backup_postgres.sh dentro del contenedor de
# Postgres. Uso: ./restore_postgres.sh /u01/RESPALDOS_BD/dovela_control_2026-09-11_020000.sql.gz
#
# ADVERTENCIA: esto sobrescribe la base de datos actual. Pensado para un
# escenario de desastre (recrear el aplicativo desde cero), no para uso normal.
set -euo pipefail

ARCHIVO="${1:?Uso: $0 <ruta-al-respaldo.sql.gz>}"
CONTENEDOR="${POSTGRES_CONTAINER:-postgres_db}"
BASE_DATOS="${POSTGRES_DB:-dovela_control}"
USUARIO="${POSTGRES_USER:-dovela_control}"
DOCKER="${DOCKER_CMD:-sudo docker}"

if [ ! -f "$ARCHIVO" ]; then
  echo "ERROR: no existe el archivo $ARCHIVO" >&2
  exit 1
fi

echo "Esto va a SOBRESCRIBIR la base de datos '$BASE_DATOS' del contenedor '$CONTENEDOR'"
echo "con el contenido de: $ARCHIVO"
read -r -p "Escribe SI (mayúsculas) para continuar: " CONFIRMACION
if [ "$CONFIRMACION" != "SI" ]; then
  echo "Cancelado."
  exit 1
fi

gunzip -c "$ARCHIVO" | $DOCKER exec -i "$CONTENEDOR" psql -U "$USUARIO" -d "$BASE_DATOS"

echo "Restauración completa desde: $ARCHIVO"

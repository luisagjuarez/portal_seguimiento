#!/bin/sh
set -eu

CONFIG_FILE=/usr/share/nginx/html/dovela_control/config.js
API_BASE_URL="${API_BASE_URL:-http://localhost:5173/dovela_control}"

sed "s|API_BASE_URL_PLACEHOLDER|${API_BASE_URL}|g" /usr/share/nginx/html/dovela_control/config.js.template > "$CONFIG_FILE"

exec nginx -g "daemon off;"

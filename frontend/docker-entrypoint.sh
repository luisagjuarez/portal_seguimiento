#!/bin/sh
set -eu

CONFIG_FILE=/usr/share/nginx/html/config.js
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

sed "s|API_BASE_URL_PLACEHOLDER|${API_BASE_URL}|g" /usr/share/nginx/html/config.js.template > "$CONFIG_FILE"

exec nginx -g "daemon off;"

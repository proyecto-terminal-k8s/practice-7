#!/usr/bin/env bash

set -euo pipefail

BACKEND_URL="${1:-http://localhost:8080}"
INTERVAL="${2:-2}"
NAMESPACE="${NAMESPACE:-practice-7}"

if ! [[ "$INTERVAL" =~ ^[0-9]+([.][0-9]+)?$ ]] || ! awk "BEGIN { exit !($INTERVAL > 0) }"; then
  printf 'El intervalo debe ser un número mayor que cero: %s\n' "$INTERVAL" >&2
  printf 'Uso: %s [URL_BACKEND] [INTERVALO_SEGUNDOS]\n' "$0" >&2
  exit 2
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v kubectl >/dev/null 2>&1; then
  echo "Se requieren curl y kubectl instalados y disponibles en PATH." >&2
  exit 2
fi

request=0

echo "Monitoreando $BACKEND_URL (namespace: $NAMESPACE; intervalo: ${INTERVAL}s)"
echo "Presiona Ctrl+C para terminar."

while true; do
  request=$((request + 1))
  timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

  if response="$(curl --silent --show-error --max-time 5 \
    --write-out $'\n%{http_code}' \
    --get \
    --data-urlencode "numero1=$request" \
    --data-urlencode "numero2=1" \
    "$BACKEND_URL/api/v1/calculadora/sumar" 2>&1)"; then
    http_code="${response##*$'\n'}"
    body="${response%$'\n'*}"
    printf '\n[%s] Petición #%d: HTTP %s\n%s\n' "$timestamp" "$request" "$http_code" "$body"
  else
    printf '\n[%s] Petición #%d fallida: %s\n' "$timestamp" "$request" "$response"
  fi

  echo "--- Estado del archivo de solicitudes y última limpieza ---"
  if ! kubectl exec -n "$NAMESPACE" deployment/calculadora-backend -- sh -c '
    log=/app/logs/api-requests.txt
    if [ -s "$log" ]; then
      echo "Últimas solicitudes:"
      tail -n 5 "$log"
    else
      echo "api-requests.txt está vacío (todavía no hubo solicitudes o el Job lo limpió)."
    fi

    latest=$(find /app/logs -maxdepth 1 -type f -name "api-requests-cleanup-*.txt" | sort | tail -n 1)
    if [ -n "$latest" ]; then
      printf "Última limpieza (%s): " "${latest##*/}"
      tail -n 1 "$latest"
    else
      echo "Aún no hay registros de limpieza."
    fi
  '; then
    echo "No se pudieron leer los logs. Verifica que el backend esté listo y el PVC montado." >&2
  fi

  sleep "$INTERVAL"
done

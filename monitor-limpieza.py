#!/usr/bin/env python3

import argparse
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen


LOG_STATUS_COMMAND = """
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
"""


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("debe ser un entero mayor que cero") from error
    if number < 1:
        raise argparse.ArgumentTypeError("debe ser un entero mayor que cero")
    return number


def positive_float(value):
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("debe ser un número mayor que cero") from error
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("debe ser un número mayor que cero")
    return number


def parse_args():
    parser = argparse.ArgumentParser(
        description="Envía solicitudes a la calculadora y muestra el estado de los logs."
    )
    parser.add_argument(
        "-u", "--url", default="http://localhost:8080",
        help="URL base del backend (por defecto: http://localhost:8080)",
    )
    parser.add_argument(
        "-n", "--requests-per-interval", type=positive_integer, default=1,
        help="peticiones en cada grupo (por defecto: 1)",
    )
    parser.add_argument(
        "-i", "--interval", type=positive_float, default=2,
        help="segundos de pausa entre grupos (por defecto: 2)",
    )
    parser.add_argument(
        "--namespace", default=os.environ.get("NAMESPACE", "practice-7"),
        help="namespace de Kubernetes (por defecto: practice-7)",
    )
    args = parser.parse_args()

    parsed_url = urlsplit(args.url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        parser.error("--url debe ser una URL HTTP o HTTPS válida")
    return args


def send_request(url, request_number):
    query = urlencode({"numero1": request_number, "numero2": 1})
    endpoint = f"{url.rstrip('/')}/api/v1/calculadora/sumar?{query}"
    request_url = endpoint
    try:
        with urlopen(request_url, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body, None
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return error.code, body, None
    except (URLError, TimeoutError, OSError) as error:
        return None, "", str(error)


def show_progress(group_number, completed, total):
    width = 24
    filled = width * completed // total
    bar = "#" * filled + "-" * (width - filled)
    line = f"Grupo {group_number} [{bar}] {completed}/{total}"
    if sys.stdout.isatty():
        print(f"\r{line}", end="", flush=True)
    else:
        print(line, flush=True)


def show_backend_logs(namespace):
    result = subprocess.run(
        [
            "kubectl", "exec", "-n", namespace, "deployment/calculadora-backend",
            "--", "sh", "-c", LOG_STATUS_COMMAND,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode:
        detail = result.stderr.strip() or f"kubectl terminó con código {result.returncode}"
        print(f"No se pudieron leer los logs: {detail}", file=sys.stderr)


def monitor(args):
    if not shutil.which("kubectl"):
        print("Se requiere kubectl instalado y disponible en PATH.", file=sys.stderr)
        return 2

    print(
        f"Monitoreando {args.url} (namespace: {args.namespace}; "
        f"peticiones por intervalo: {args.requests_per_interval}; "
        f"intervalo: {args.interval:g}s)"
    )
    print("Presiona Ctrl+C para terminar.")

    request_number = 0
    group_number = 0
    while True:
        group_number += 1
        results = []
        for completed in range(1, args.requests_per_interval + 1):
            request_number += 1
            timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
            status, body, error = send_request(args.url, request_number)
            results.append((timestamp, request_number, status, body, error))
            show_progress(group_number, completed, args.requests_per_interval)

        if sys.stdout.isatty():
            print()
        for timestamp, number, status, body, error in results:
            if error:
                print(f"[{timestamp}] Petición #{number} fallida: {error}")
            else:
                print(f"[{timestamp}] Petición #{number}: HTTP {status}")
                if body:
                    print(body)

        print("--- Estado del archivo de solicitudes y última limpieza ---")
        show_backend_logs(args.namespace)
        print(f"Próximo grupo en {args.interval:g}s. Presiona Ctrl+C para detener.")
        time.sleep(args.interval)


def main():
    args = parse_args()
    try:
        return monitor(args)
    except KeyboardInterrupt:
        print("\nMonitoreo detenido.")
        return 130


if __name__ == "__main__":
    sys.exit(main())

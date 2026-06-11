#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HMI_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON="${HMI_PYTHON:-$ROOT/.venv/bin/python}"
UVICORN="${HMI_UVICORN:-$ROOT/.venv/bin/uvicorn}"
NPM="${HMI_NPM:-npm}"

HMI_NODES="${HMI_NODES:-N01}"
HMI_STARTUP_SEQUENCE="${HMI_STARTUP_SEQUENCE:-1}"
HMI_COMMAND_SERVER="${HMI_COMMAND_SERVER:-1}"
HMI_COMMAND_ENDPOINT="${HMI_COMMAND_ENDPOINT:-tcp://*:3334}"
HMI_FORWARD_DATA="${HMI_FORWARD_DATA:-0}"
HMI_BACKEND_HOST="${HMI_BACKEND_HOST:-0.0.0.0}"
HMI_BACKEND_PORT="${HMI_BACKEND_PORT:-8000}"
HMI_FRONTEND_MODE="${HMI_FRONTEND_MODE:-static}"
HMI_FRONTEND_HOST="${HMI_FRONTEND_HOST:-0.0.0.0}"
HMI_FRONTEND_PORT="${HMI_FRONTEND_PORT:-5173}"

PIDS=()

truthy() {
  case "${1,,}" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

start_process() {
  local name="$1"
  shift
  echo "Starting $name: $*"
  "$@" &
  PIDS+=("$!")
}

start_process_in_dir() {
  local name="$1"
  local directory="$2"
  shift 2
  echo "Starting $name in $directory: $*"
  (
    cd "$directory"
    exec "$@"
  ) &
  PIDS+=("$!")
}

stop_all() {
  echo "Stopping HMI stack..."
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done

  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
}

trap stop_all EXIT INT TERM

require_file "$PYTHON"
require_file "$UVICORN"
require_file "$ROOT/run_zmq_server.py"
require_file "$ROOT/backend/app/main.py"
if [[ "$HMI_FRONTEND_MODE" == "static" ]]; then
  require_file "$ROOT/frontend/dist/index.html"
else
  require_file "$ROOT/frontend/package.json"
fi

ZMQ_ARGS=(--nodes "$HMI_NODES" --command-endpoint "$HMI_COMMAND_ENDPOINT")
if ! truthy "$HMI_STARTUP_SEQUENCE"; then
  ZMQ_ARGS+=(--no-startup-sequence)
fi
if ! truthy "$HMI_COMMAND_SERVER"; then
  ZMQ_ARGS+=(--no-command-server)
fi
if truthy "$HMI_FORWARD_DATA"; then
  ZMQ_ARGS+=(--forward-data)
fi

start_process "CAN/ZMQ server" "$PYTHON" "$ROOT/run_zmq_server.py" "${ZMQ_ARGS[@]}"

start_process_in_dir "FastAPI backend" "$ROOT/backend" \
  "$UVICORN" app.main:app --host "$HMI_BACKEND_HOST" --port "$HMI_BACKEND_PORT"

if [[ "$HMI_FRONTEND_MODE" == "static" ]]; then
  FRONTEND_URL="http://127.0.0.1:$HMI_BACKEND_PORT"
else
  FRONTEND_SCRIPT="dev"
  if [[ "$HMI_FRONTEND_MODE" == "preview" ]]; then
    FRONTEND_SCRIPT="preview"
  fi

  start_process_in_dir "React frontend" "$ROOT/frontend" \
    "$NPM" run "$FRONTEND_SCRIPT" -- --host "$HMI_FRONTEND_HOST" --port "$HMI_FRONTEND_PORT"

  FRONTEND_URL="http://127.0.0.1:$HMI_FRONTEND_PORT"
fi

echo "HMI stack running:"
echo "  Backend:  http://127.0.0.1:$HMI_BACKEND_PORT"
echo "  Frontend: $FRONTEND_URL ($HMI_FRONTEND_MODE)"
echo "  ZMQ telemetry: tcp://127.0.0.1:3333"
echo "  ZMQ commands:  ${HMI_COMMAND_ENDPOINT/\*/127.0.0.1}"

while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "A HMI process stopped unexpectedly; shutting down stack." >&2
      exit 1
    fi
  done
  sleep 2
done

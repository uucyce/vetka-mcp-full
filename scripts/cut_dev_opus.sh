#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLIENT_DIR="$ROOT_DIR/client"
PORT="${CUT_OPUS_PORT:-3111}"
HOST="${CUT_OPUS_HOST:-127.0.0.1}"
SANDBOX_HINT="${CUT_OPUS_SANDBOX_HINT:-opus_cut_packaging_sandbox}"

usage() {
  cat <<EOF
Usage: scripts/cut_dev_opus.sh <check-port|web|tauri-dev|tauri-build>

Reserved port: ${PORT}
Sandbox hint: ${SANDBOX_HINT}
EOF
}

port_busy() {
  lsof -ti tcp:"$PORT" >/dev/null 2>&1
}

fail_if_port_busy() {
  if port_busy; then
    echo "Reserved CUT Opus port ${PORT} is already in use. Refusing to steal another lane."
    exit 2
  fi
}

cmd="${1:-}"
case "$cmd" in
  check-port)
    if port_busy; then
      echo "BUSY:${PORT}"
      exit 2
    fi
    echo "FREE:${PORT}"
    ;;
  web)
    fail_if_port_busy
    cd "$CLIENT_DIR"
    exec npm run dev:cut:opus
    ;;
  tauri-dev)
    fail_if_port_busy
    cd "$CLIENT_DIR"
    exec npm run tauri:dev:cut:opus
    ;;
  tauri-build)
    cd "$CLIENT_DIR"
    exec npm run tauri:build:cut:opus
    ;;
  *)
    usage
    exit 1
    ;;
esac

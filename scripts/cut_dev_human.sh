#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLIENT_DIR="$ROOT_DIR/client"
PORT="${CUT_HUMAN_PORT:-3011}"
HOST="${CUT_HUMAN_HOST:-127.0.0.1}"
LANE_NAME="${CUT_HUMAN_LANE_NAME:-human_review_cut_lane}"

usage() {
  cat <<EOF
Usage: scripts/cut_dev_human.sh <check-port|web|tauri-dev|tauri-build>

Reserved port: ${PORT}
Lane: ${LANE_NAME}
EOF
}

port_busy() {
  lsof -ti tcp:"$PORT" >/dev/null 2>&1
}

fail_if_port_busy() {
  if port_busy; then
    echo "Reserved CUT human-review port ${PORT} is already in use. Refusing to steal another lane."
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
    exec npm run dev:cut:human
    ;;
  tauri-dev)
    fail_if_port_busy
    cd "$CLIENT_DIR"
    exec npm run tauri:dev:cut:human
    ;;
  tauri-build)
    cd "$CLIENT_DIR"
    exec npm run tauri:build:cut:human
    ;;
  *)
    usage
    exit 1
    ;;
esac

#!/bin/bash
# VETKA FastAPI Server
# Phase 39.8 - Production ready

set -eo pipefail

echo ""
echo "  Starting VETKA FastAPI Server..."
echo "  Port: 5001"
echo "  Docs: http://localhost:5001/docs"
echo ""

# Canonical runtime environment: .venv only
if [ ! -d ".venv" ]; then
    echo "  ERROR: .venv not found."
    echo "  Create it with: python3 -m venv .venv"
    exit 1
fi
source .venv/bin/activate
PYTHON_BIN=".venv/bin/python"

# Load centralized runtime policy (if present).
# Priority:
# 1) shell-exported vars
# 2) .env
# 3) config/runtime.env
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [ -f "config/runtime.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "config/runtime.env"
  set +a
fi

# Harden local loopback routing against VPN/proxy interference.
export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost}"
export no_proxy="${no_proxy:-127.0.0.1,localhost}"
export QDRANT_HOST="${QDRANT_HOST:-127.0.0.1}"
export QDRANT_PORT="${QDRANT_PORT:-6333}"
export VETKA_WATCHER_VERBOSE="${VETKA_WATCHER_VERBOSE:-0}"
export VETKA_TREE_VERBOSE="${VETKA_TREE_VERBOSE:-0}"
export VETKA_CONTEXT_PACKER_ENABLED="${VETKA_CONTEXT_PACKER_ENABLED:-true}"
export VETKA_CONTEXT_PACKER_JEPA_ENABLE="${VETKA_CONTEXT_PACKER_JEPA_ENABLE:-true}"
export VETKA_CONTEXT_PACKER_TOKEN_PRESSURE="${VETKA_CONTEXT_PACKER_TOKEN_PRESSURE:-0.80}"
export VETKA_CONTEXT_PACKER_DOCS_THRESHOLD="${VETKA_CONTEXT_PACKER_DOCS_THRESHOLD:-18}"
export VETKA_CONTEXT_PACKER_ENTROPY_THRESHOLD="${VETKA_CONTEXT_PACKER_ENTROPY_THRESHOLD:-2.50}"
export VETKA_CONTEXT_PACKER_MODALITY_THRESHOLD="${VETKA_CONTEXT_PACKER_MODALITY_THRESHOLD:-2}"
export VETKA_CONTEXT_PACKER_HYSTERESIS_ON="${VETKA_CONTEXT_PACKER_HYSTERESIS_ON:-3}"
export VETKA_CONTEXT_PACKER_HYSTERESIS_OFF="${VETKA_CONTEXT_PACKER_HYSTERESIS_OFF:-2}"
export VETKA_CONTEXT_PACKER_RECENT_MAX="${VETKA_CONTEXT_PACKER_RECENT_MAX:-300}"

JEPA_RUNTIME_PID=""

cleanup() {
  if [ -n "$JEPA_RUNTIME_PID" ] && kill -0 "$JEPA_RUNTIME_PID" 2>/dev/null; then
    echo "  Stopping JEPA runtime (pid=$JEPA_RUNTIME_PID)..."
    kill -TERM "$JEPA_RUNTIME_PID" 2>/dev/null || true
    wait "$JEPA_RUNTIME_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

# MARKER_155.P3_5.JEPA_AUTOSTART:
# Start local JEPA runtime alongside main server by default.
export MCC_JEPA_HTTP_ENABLE="${MCC_JEPA_HTTP_ENABLE:-1}"
export MCC_JEPA_HTTP_PORT="${MCC_JEPA_HTTP_PORT:-8099}"
export MCC_JEPA_HTTP_HOST="${MCC_JEPA_HTTP_HOST:-127.0.0.1}"
export MCC_JEPA_HTTP_URL="${MCC_JEPA_HTTP_URL:-http://${MCC_JEPA_HTTP_HOST}:${MCC_JEPA_HTTP_PORT}/embed_texts}"

if [ "${MCC_JEPA_HTTP_ENABLE}" = "1" ] || [ "${MCC_JEPA_HTTP_ENABLE}" = "true" ]; then
  if lsof -nP -iTCP:"${MCC_JEPA_HTTP_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "  JEPA runtime already listening on port ${MCC_JEPA_HTTP_PORT}."
  else
    echo "  Starting JEPA runtime on ${MCC_JEPA_HTTP_HOST}:${MCC_JEPA_HTTP_PORT}..."
    "${PYTHON_BIN}" -m uvicorn src.services.jepa_http_server:app \
      --host "${MCC_JEPA_HTTP_HOST}" \
      --port "${MCC_JEPA_HTTP_PORT}" \
      --log-level warning >/tmp/vetka_jepa_runtime.log 2>&1 &
    JEPA_RUNTIME_PID=$!

    # Wait up to 5s for /health
    for _ in $(seq 1 25); do
      if curl -fsS "http://${MCC_JEPA_HTTP_HOST}:${MCC_JEPA_HTTP_PORT}/health" >/dev/null 2>&1; then
        echo "  JEPA runtime is up."
        break
      fi
      sleep 0.2
    done

    if ! curl -fsS "http://${MCC_JEPA_HTTP_HOST}:${MCC_JEPA_HTTP_PORT}/health" >/dev/null 2>&1; then
      echo "  WARNING: JEPA runtime healthcheck failed; strict architecture mode may show UNAVAILABLE."
    fi
  fi
fi

# Run with uvicorn (reload only if explicitly enabled)
if [ "${VETKA_RELOAD:-0}" = "1" ] || [ "${VETKA_RELOAD:-false}" = "true" ]; then
  "${PYTHON_BIN}" -m uvicorn main:socket_app \
    --host 0.0.0.0 \
    --port 5001 \
    --reload \
    --reload-exclude "data/playgrounds/*" \
    --reload-exclude ".playgrounds/*" \
    --reload-exclude "data/changelog/*" \
    --reload-exclude "data/pipeline_history.json" \
    --reload-exclude "data/pipeline_tasks.json"
else
  "${PYTHON_BIN}" -m uvicorn main:socket_app --host 0.0.0.0 --port 5001
fi

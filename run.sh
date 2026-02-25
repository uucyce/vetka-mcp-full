#!/bin/bash
# VETKA FastAPI Server
# Phase 39.8 - Production ready

echo ""
echo "  Starting VETKA FastAPI Server..."
echo "  Port: 5001"
echo "  Docs: http://localhost:5001/docs"
echo ""

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

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
    uvicorn src.services.jepa_http_server:app \
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
  uvicorn main:socket_app \
    --host 0.0.0.0 \
    --port 5001 \
    --reload \
    --reload-exclude "data/playgrounds/*" \
    --reload-exclude ".playgrounds/*" \
    --reload-exclude "data/changelog/*" \
    --reload-exclude "data/pipeline_history.json" \
    --reload-exclude "data/pipeline_tasks.json"
else
  uvicorn main:socket_app --host 0.0.0.0 --port 5001
fi

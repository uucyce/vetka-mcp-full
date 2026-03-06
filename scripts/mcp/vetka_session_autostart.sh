#!/bin/zsh
set -u

PROJECT_ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
INIT_SCRIPT="$PROJECT_ROOT/scripts/mcp/vetka_session_init_ws.py"
LOCK_FILE="/tmp/vetka_session_autoinit.lock"
LOG_FILE="/tmp/vetka_session_autoinit.log"
TTL_SECONDS="${VETKA_SESSION_AUTOINIT_TTL:-900}"
SOURCE_TAG="manual"
FORCE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE_TAG="${2:-manual}"
      shift 2
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [[ "$FORCE" != "true" && -f "$LOCK_FILE" ]]; then
  now_epoch="$(date +%s)"
  lock_epoch="$(stat -f %m "$LOCK_FILE" 2>/dev/null || echo 0)"
  age=$((now_epoch - lock_epoch))
  if [[ "$age" -lt "$TTL_SECONDS" ]]; then
    exit 0
  fi
fi

health_ok="false"
if curl -fsS --max-time 2 http://127.0.0.1:5001/health >/dev/null 2>&1; then
  health_ok="true"
elif curl -fsS --max-time 2 http://127.0.0.1:5001/api/health >/dev/null 2>&1; then
  health_ok="true"
fi

if [[ "$health_ok" != "true" ]]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [$SOURCE_TAG] skip: VETKA health endpoint unavailable" >>"$LOG_FILE"
  exit 0
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

result="$("$PYTHON_BIN" "$INIT_SCRIPT" --user-id danila --compress true --include-pinned true --include-viewport true --max-context-tokens 4000 2>&1)"
status=$?

if [[ $status -eq 0 ]]; then
  touch "$LOCK_FILE"
  echo "$(date '+%Y-%m-%d %H:%M:%S') [$SOURCE_TAG] ok: $result" >>"$LOG_FILE"
  exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') [$SOURCE_TAG] fail($status): $result" >>"$LOG_FILE"
exit 0


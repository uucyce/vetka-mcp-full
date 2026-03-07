#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

ok() { echo "[ok] $1"; }
warn() { echo "[warn] $1"; }
fail() { echo "[fail] $1"; }

check_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "command '$cmd' found"
  else
    fail "command '$cmd' missing"
  fi
}

echo "[doctor] root: $ROOT_DIR"

check_cmd python3
check_cmd npm
check_cmd curl

if [[ -d ".venv" ]]; then
  ok ".venv exists"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python - <<'PY'
mods = ["fastapi", "uvicorn", "requests", "qdrant_client", "socketio"]
missing = []
for m in mods:
    try:
        __import__(m)
    except Exception:
        missing.append(m)
if missing:
    print("[warn] missing python modules:", ", ".join(missing))
else:
    print("[ok] core python modules importable")
PY
else
  fail ".venv missing"
fi

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "docker is running"
    if docker ps --format '{{.Names}}' | rg -q '^qdrant$'; then
      ok "qdrant container is running"
      if curl -fsS http://127.0.0.1:6333/health >/dev/null 2>&1; then
        ok "qdrant health endpoint reachable"
      else
        warn "qdrant container running but /health not reachable"
      fi
    else
      warn "qdrant container is not running (docker compose up -d qdrant)"
    fi
  else
    warn "docker installed but daemon is not running"
  fi
else
  warn "docker not installed"
fi

if curl -fsS http://127.0.0.1:5001/api/health >/dev/null 2>&1; then
  ok "backend health: /api/health"
else
  warn "backend is not reachable on http://127.0.0.1:5001/api/health"
fi

if curl -fsS http://127.0.0.1:5173 >/dev/null 2>&1; then
  ok "frontend dev server reachable on :5173"
else
  warn "frontend dev server is not running on :5173"
fi

echo "[doctor] done"

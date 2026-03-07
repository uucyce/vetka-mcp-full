#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
AUTO_YES=0
WITH_OPTIONAL=0
START_BACKEND=0
START_FRONTEND=0

usage() {
  cat <<USAGE
bootstrap_mycelium.sh - smart bootstrap for MYCELIUM-first users

Usage:
  ./scripts/install/bootstrap_mycelium.sh [options]

Options:
  -y, --yes             Non-interactive mode (accept defaults)
      --with-optional   Start optional infra (weaviate, ollama) in addition to qdrant
      --start-backend   Start backend via ./run.sh after install
      --start-frontend  Start frontend dev server after install
  -h, --help            Show help
USAGE
}

ask() {
  local prompt="$1"
  if [[ "$AUTO_YES" -eq 1 ]]; then
    return 0
  fi
  read -r -p "$prompt [y/N]: " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[bootstrap] missing required command: $cmd" >&2
    return 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes) AUTO_YES=1 ;;
    --with-optional) WITH_OPTIONAL=1 ;;
    --start-backend) START_BACKEND=1 ;;
    --start-frontend) START_FRONTEND=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

cd "$ROOT_DIR"

echo "[bootstrap] root: $ROOT_DIR"

require_cmd "$PYTHON_BIN"
require_cmd pip || true
require_cmd npm
require_cmd curl

if [[ ! -f "requirements.txt" || ! -f "client/package.json" || ! -f "run.sh" ]]; then
  echo "[bootstrap] not a VETKA root: requirements.txt/client/package.json/run.sh not found" >&2
  exit 1
fi

if [[ ! -f ".env" && -f ".env.example" ]]; then
  echo "[bootstrap] .env not found"
  if ask "Create .env from .env.example?"; then
    cp .env.example .env
    echo "[bootstrap] created .env"
  fi
fi

if [[ ! -d ".venv" ]]; then
  echo "[bootstrap] creating Python venv (.venv)"
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[bootstrap] installing backend dependencies"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

echo "[bootstrap] installing frontend dependencies"
(
  cd client
  npm install
)

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "[bootstrap] docker detected"
  if ask "Start required infra (qdrant)?"; then
    docker compose up -d qdrant
  fi
  if [[ "$WITH_OPTIONAL" -eq 1 ]]; then
    echo "[bootstrap] starting optional infra: weaviate ollama"
    docker compose up -d weaviate ollama
  fi
else
  echo "[bootstrap] docker is not available/running; skipping infra startup"
fi

if [[ "$START_BACKEND" -eq 1 ]]; then
  echo "[bootstrap] starting backend (./run.sh)"
  ./run.sh
fi

if [[ "$START_FRONTEND" -eq 1 ]]; then
  echo "[bootstrap] starting frontend (npm run dev)"
  (
    cd client
    npm run dev
  )
fi

echo "[bootstrap] done"
echo "[bootstrap] next checks:"
echo "  curl http://127.0.0.1:5001/api/health"
echo "  ./scripts/install/doctor.sh"

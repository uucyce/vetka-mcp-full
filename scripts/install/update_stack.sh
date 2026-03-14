#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
AUTO_YES=0
SKIP_GIT=0

usage() {
  cat <<USAGE
update_stack.sh - update VETKA runtime and dependencies

Usage:
  ./scripts/install/update_stack.sh [options]

Options:
  -y, --yes       Non-interactive mode
      --skip-git  Skip git pull/rebase step
  -h, --help      Show help
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes) AUTO_YES=1 ;;
    --skip-git) SKIP_GIT=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

cd "$ROOT_DIR"

if [[ "$SKIP_GIT" -eq 0 ]]; then
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "[update] working tree is dirty; skipping git pull/rebase"
  else
    if ask "Run git pull --rebase on current branch?"; then
      git pull --rebase
    fi
  fi
fi

if [[ ! -d ".venv" ]]; then
  echo "[update] .venv not found, creating"
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[update] updating backend dependencies"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

echo "[update] updating frontend dependencies"
(
  cd client
  npm install
)

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if ask "Pull newer docker images for qdrant/weaviate/ollama?"; then
    docker compose pull qdrant weaviate ollama || true
  fi
fi

echo "[update] done"

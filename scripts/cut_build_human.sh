#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLIENT_DIR="$ROOT_DIR/client"

cd "$CLIENT_DIR"
exec npx vite build --config src-tauri/vite.cut.human.config.mjs

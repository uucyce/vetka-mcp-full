#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:3001}"
OUT_DIR="${2:-output/playwright/mcc}"
OUT_FILE="$OUT_DIR/mcc_drilldown_$(date +%Y%m%d_%H%M%S).png"

mkdir -p "$OUT_DIR"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required (Node.js/npm)." >&2
  exit 1
fi

export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"

if [[ ! -x "$PWCLI" ]]; then
  echo "Playwright skill wrapper not found: $PWCLI" >&2
  exit 1
fi

echo "[capture] open: $URL"
"$PWCLI" open "$URL"

echo "[capture] snapshot"
"$PWCLI" snapshot >/dev/null

echo "[capture] screenshot -> $OUT_FILE"
"$PWCLI" screenshot "$OUT_FILE" >/dev/null

echo "$OUT_FILE"

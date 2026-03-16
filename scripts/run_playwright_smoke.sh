#!/usr/bin/env bash
# MARKER_186.1: Playwright smoke runner for REFLEX integration.
# Called by REFLEX tool catalog when agent edits UI files.
# Usage: scripts/run_playwright_smoke.sh [spec_pattern]
#
# Auto-installs node_modules and Chromium on first run.
# Subsequent runs skip install (< 1s overhead).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLIENT_DIR="$ROOT/client"
SPEC_PATTERN="${1:-smoke}"
LOCK_FILE="$CLIENT_DIR/.playwright-ready"

cd "$CLIENT_DIR"

# --- Auto-install (idempotent, skips if already done) ---
if [ ! -f "$LOCK_FILE" ] || [ ! -d "node_modules/@playwright" ]; then
  echo "[setup] Installing node_modules..."
  npm install --prefer-offline --no-audit --no-fund 2>&1 | tail -3

  echo "[setup] Installing Chromium browser..."
  npx playwright install chromium 2>&1 | tail -3

  # Stamp: skip install next time
  date -u +%Y-%m-%dT%H:%M:%SZ > "$LOCK_FILE"
  echo "[setup] Done. Stamp: $LOCK_FILE"
fi

# --- Run tests ---
echo "=== VETKA CUT Playwright Smoke ==="
echo "Pattern: $SPEC_PATTERN"
echo "Specs:   $CLIENT_DIR/e2e/"

npx playwright test --grep "$SPEC_PATTERN" --workers=1 --reporter=list 2>&1
EXIT_CODE=$?

echo "=== Playwright exit: $EXIT_CODE ==="
exit $EXIT_CODE

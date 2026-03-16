#!/usr/bin/env bash
# MARKER_186.1: Playwright smoke runner for REFLEX integration.
# Called by REFLEX tool catalog when agent edits UI files.
# Usage: scripts/run_playwright_smoke.sh [spec_pattern]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLIENT_DIR="$ROOT/client"

SPEC_PATTERN="${1:-smoke}"

cd "$CLIENT_DIR"

echo "=== VETKA CUT Playwright Smoke ==="
echo "Pattern: $SPEC_PATTERN"
echo "Dir: $CLIENT_DIR/e2e/"

# Ensure playwright browsers installed
npx playwright install chromium --with-deps 2>/dev/null || true

# Run matching specs, workers=1 to avoid port contention
npx playwright test --grep "$SPEC_PATTERN" --workers=1 --reporter=list 2>&1

EXIT_CODE=$?
echo "=== Playwright exit: $EXIT_CODE ==="
exit $EXIT_CODE

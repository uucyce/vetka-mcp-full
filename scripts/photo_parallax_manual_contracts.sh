#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
OUT_ROOT="$LAB/output/manual_contracts"

SAMPLE_ID="${1:-cassette-closeup}"
OUT_DIR="$OUT_ROOT/$SAMPLE_ID"

mkdir -p "$OUT_DIR"

cd "$LAB"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:1434 | xargs -r kill >/dev/null 2>&1 || true
fi

PARALLAX_LAB_SAMPLE_ID="$SAMPLE_ID" \
PARALLAX_LAB_MANUAL_CONTRACT_DIR="$OUT_DIR" \
npx playwright test e2e/parallax_manual_contracts.spec.ts --reporter=line

echo "MARKER_180.PARALLAX.MANUAL_CONTRACTS.SAMPLE=$SAMPLE_ID"
echo "MARKER_180.PARALLAX.MANUAL_CONTRACTS.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.MANUAL_CONTRACTS.HINTS=$OUT_DIR/manual_hints.json"
echo "MARKER_180.PARALLAX.MANUAL_CONTRACTS.GROUPS=$OUT_DIR/group_boxes.json"
echo "MARKER_180.PARALLAX.MANUAL_CONTRACTS.SCREENSHOT=$OUT_DIR/manual_contracts_selection.png"

if [[ "${2:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  open "$OUT_DIR/manual_contracts_selection.png"
fi

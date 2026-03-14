#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
OUT_DIR="$LAB/output/layered_edit_flow"

SAMPLE_IDS="${1:-cassette-closeup,keyboard-hands,hover-politsia}"

mkdir -p "$OUT_DIR"

cd "$LAB"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:1434 | xargs -r kill >/dev/null 2>&1 || true
fi

PARALLAX_LAB_LAYERED_SAMPLE_IDS="$SAMPLE_IDS" \
PARALLAX_LAB_LAYERED_DIR="$OUT_DIR" \
npx playwright test e2e/parallax_layered_workflow.spec.ts --reporter=line

echo "MARKER_180.PARALLAX.LAYERED.SAMPLES=$SAMPLE_IDS"
echo "MARKER_180.PARALLAX.LAYERED.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.LAYERED.SUMMARY=$OUT_DIR/layered_edit_flow_summary.json"

if [[ "${2:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  FIRST_SAMPLE="${SAMPLE_IDS%%,*}"
  open "$OUT_DIR/$FIRST_SAMPLE/layered_selection.png"
fi

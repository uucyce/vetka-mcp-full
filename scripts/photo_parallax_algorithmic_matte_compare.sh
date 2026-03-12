#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
OUT_DIR="$LAB/output/algorithmic_matte_compare"

SAMPLE_IDS="${1:-cassette-closeup,keyboard-hands,hover-politsia}"

mkdir -p "$OUT_DIR"

cd "$LAB"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:1434 | xargs -r kill >/dev/null 2>&1 || true
fi

PARALLAX_LAB_COMPARE_SAMPLE_IDS="$SAMPLE_IDS" \
PARALLAX_LAB_MATTE_COMPARE_DIR="$OUT_DIR" \
npx playwright test e2e/parallax_algorithmic_matte_compare.spec.ts --reporter=line

echo "MARKER_180.PARALLAX.MATTE_COMPARE.SAMPLES=$SAMPLE_IDS"
echo "MARKER_180.PARALLAX.MATTE_COMPARE.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.MATTE_COMPARE.SUMMARY=$OUT_DIR/algorithmic_matte_compare_summary.json"

if [[ "${2:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  FIRST_SAMPLE="${SAMPLE_IDS%%,*}"
  open "$OUT_DIR/$FIRST_SAMPLE/algorithmic_matte_selection.png"
fi

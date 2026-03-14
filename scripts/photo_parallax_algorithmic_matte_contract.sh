#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
OUT_ROOT="$LAB/output/algorithmic_matte_contract"

SAMPLE_ID="${1:-cassette-closeup}"
OUT_DIR="$OUT_ROOT/$SAMPLE_ID"

mkdir -p "$OUT_DIR"

cd "$LAB"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:1434 | xargs -r kill >/dev/null 2>&1 || true
fi

PARALLAX_LAB_SAMPLE_ID="$SAMPLE_ID" \
PARALLAX_LAB_MATTE_CONTRACT_DIR="$OUT_DIR" \
npx playwright test e2e/parallax_algorithmic_matte_contract.spec.ts --reporter=line

echo "MARKER_180.PARALLAX.MATTE_CONTRACT.SAMPLE=$SAMPLE_ID"
echo "MARKER_180.PARALLAX.MATTE_CONTRACT.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.MATTE_CONTRACT.JSON=$OUT_DIR/algorithmic_matte.json"
echo "MARKER_180.PARALLAX.MATTE_CONTRACT.STATE=$OUT_DIR/algorithmic_matte_state.json"
echo "MARKER_180.PARALLAX.MATTE_CONTRACT.SCREENSHOT=$OUT_DIR/algorithmic_matte_selection.png"

if [[ "${2:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  open "$OUT_DIR/algorithmic_matte_selection.png"
fi

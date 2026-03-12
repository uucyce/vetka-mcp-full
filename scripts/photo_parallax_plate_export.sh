#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
OUT_ROOT="$LAB/output/plate_exports"

SAMPLE_ID="${1:-hover-politsia}"
OUT_DIR="$OUT_ROOT/$SAMPLE_ID"

mkdir -p "$OUT_DIR"

cd "$LAB"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:1434 | xargs -r kill >/dev/null 2>&1 || true
fi

PARALLAX_LAB_SAMPLE_ID="$SAMPLE_ID" \
PARALLAX_LAB_PLATE_EXPORT_DIR="$OUT_DIR" \
npx playwright test e2e/parallax_plate_export.spec.ts --reporter=line

echo "MARKER_180.PARALLAX.PLATE_EXPORT.SAMPLE=$SAMPLE_ID"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.MANIFEST=$OUT_DIR/plate_export_manifest.json"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.LAYOUT=$OUT_DIR/plate_layout.json"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.STACK=$OUT_DIR/plate_stack.json"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.GLOBAL_DEPTH=$OUT_DIR/global_depth_bw.png"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.COMPOSITE=$OUT_DIR/plate_export_composite.png"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.DEPTH=$OUT_DIR/plate_export_depth.png"

if [[ "${2:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  open "$OUT_DIR"
fi

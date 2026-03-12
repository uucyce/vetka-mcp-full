#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
OUT_DIR="$ROOT/photo_parallax_playground/output/render_compare_multiplate"

python3 "$ROOT/scripts/photo_parallax_compare_multiplate.py" "$@"

echo "MARKER_180.PARALLAX.MULTIPLATE_COMPARE.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.MULTIPLATE_COMPARE.SUMMARY=$OUT_DIR/render_compare_multiplate_summary.json"

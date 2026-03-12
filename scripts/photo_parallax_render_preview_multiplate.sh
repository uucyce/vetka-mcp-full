#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
OUT_DIR="$ROOT/photo_parallax_playground/output/render_preview_multiplate"

python3 "$ROOT/scripts/photo_parallax_render_preview_multiplate.py" "$@"

echo "MARKER_180.PARALLAX.MULTIPLATE_RENDER.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.MULTIPLATE_RENDER.SUMMARY=$OUT_DIR/render_preview_multiplate_summary.json"

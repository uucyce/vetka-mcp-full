#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
OUT_DIR="$ROOT/photo_parallax_playground/output/render_preview_multiplate"
PRESET="quality"

for ((i=1; i<=$#; i++)); do
  if [[ "${!i}" == "--preset" ]]; then
    next=$((i + 1))
    if (( next <= $# )); then
      PRESET="${!next}"
    fi
  fi
  if [[ "${!i}" == "--outdir" ]]; then
    next=$((i + 1))
    if (( next <= $# )); then
      OUT_DIR="${!next}"
    fi
  fi
done

python3 "$ROOT/scripts/photo_parallax_render_preview_multiplate.py" "$@"

if [[ "$PRESET" != "quality" ]]; then
  OUT_DIR="$OUT_DIR/$PRESET"
fi

echo "MARKER_180.PARALLAX.MULTIPLATE_RENDER.PRESET=$PRESET"
echo "MARKER_180.PARALLAX.MULTIPLATE_RENDER.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.MULTIPLATE_RENDER.SUMMARY=$OUT_DIR/render_preview_multiplate_summary.json"

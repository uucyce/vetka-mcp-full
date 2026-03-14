#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"

if [[ $# -eq 0 ]]; then
  SAMPLES=("hover-politsia" "keyboard-hands" "truck-driver")
else
  SAMPLES=("$@")
fi

for sample in "${SAMPLES[@]}"; do
  "$ROOT/scripts/photo_parallax_plate_export.sh" "$sample" --no-open
done

echo "MARKER_180.PARALLAX.PLATE_EXPORT_BATCH.SAMPLES=${SAMPLES[*]}"

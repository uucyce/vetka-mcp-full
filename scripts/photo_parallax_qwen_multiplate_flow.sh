#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
QWEN_EXPORT_ROOT="$LAB/output/plate_exports_qwen"
QWEN_RENDER_ROOT="$LAB/output/render_preview_multiplate_qwen"

SAMPLES=("$@")
if [[ ${#SAMPLES[@]} -eq 0 ]]; then
  SAMPLES=("hover-politsia" "keyboard-hands" "truck-driver")
fi

for SAMPLE in "${SAMPLES[@]}"; do
  "$ROOT/scripts/photo_parallax_plate_export.sh" "$SAMPLE" --apply-qwen-plan --no-open
done

ARGS=()
for SAMPLE in "${SAMPLES[@]}"; do
  ARGS+=(--sample "$SAMPLE")
done

python3 "$ROOT/scripts/photo_parallax_render_preview_multiplate.py" \
  --plate-export-root "$QWEN_EXPORT_ROOT" \
  --outdir "$QWEN_RENDER_ROOT" \
  "${ARGS[@]}"

python3 "$ROOT/scripts/photo_parallax_compare_qwen_multiplate.py" \
  --manual-render-root "$LAB/output/render_preview_multiplate" \
  --qwen-render-root "$QWEN_RENDER_ROOT" \
  "${ARGS[@]}"

python3 "$ROOT/scripts/photo_parallax_qwen_plate_gate.py" \
  "${ARGS[@]}"

echo "MARKER_180.PARALLAX.QWEN_FLOW.EXPORT_ROOT=$QWEN_EXPORT_ROOT"
echo "MARKER_180.PARALLAX.QWEN_FLOW.RENDER_ROOT=$QWEN_RENDER_ROOT"
echo "MARKER_180.PARALLAX.QWEN_FLOW.COMPARE_SUMMARY=$LAB/output/render_compare_qwen_multiplate/render_compare_qwen_multiplate_summary.json"
echo "MARKER_180.PARALLAX.QWEN_FLOW.GATE_SUMMARY=$LAB/output/qwen_plate_gates/manifest.json"

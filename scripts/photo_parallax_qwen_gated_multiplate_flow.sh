#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
GATED_EXPORT_ROOT="$LAB/output/plate_exports_qwen_gated"
GATED_RENDER_ROOT="$LAB/output/render_preview_multiplate_qwen_gated"
GATED_COMPARE_ROOT="$LAB/output/render_compare_qwen_gated_multiplate"
GATED_QA_ROOT="$LAB/output/render_compare_qwen_gated_multiplate"

SAMPLES=("$@")
if [[ ${#SAMPLES[@]} -eq 0 ]]; then
  SAMPLES=("hover-politsia" "keyboard-hands" "truck-driver")
fi

for SAMPLE in "${SAMPLES[@]}"; do
  "$ROOT/scripts/photo_parallax_plate_export.sh" "$SAMPLE" --apply-qwen-gate --no-open
done

ARGS=()
for SAMPLE in "${SAMPLES[@]}"; do
  ARGS+=(--sample "$SAMPLE")
done

python3 "$ROOT/scripts/photo_parallax_render_preview_multiplate.py" \
  --plate-export-root "$GATED_EXPORT_ROOT" \
  --outdir "$GATED_RENDER_ROOT" \
  "${ARGS[@]}"

python3 "$ROOT/scripts/photo_parallax_compare_qwen_multiplate.py" \
  --manual-render-root "$LAB/output/render_preview_multiplate" \
  --qwen-render-root "$GATED_RENDER_ROOT" \
  --outdir "$GATED_COMPARE_ROOT" \
  "${ARGS[@]}"

python3 "$ROOT/scripts/photo_parallax_build_gated_batch_qa.py" \
  --export-root "$GATED_EXPORT_ROOT" \
  --render-summary "$GATED_RENDER_ROOT/render_preview_multiplate_summary.json" \
  --compare-summary "$GATED_COMPARE_ROOT/render_compare_qwen_multiplate_summary.json" \
  --outdir "$GATED_QA_ROOT" \
  "${ARGS[@]}"

echo "MARKER_180.PARALLAX.QWEN_GATED_FLOW.EXPORT_ROOT=$GATED_EXPORT_ROOT"
echo "MARKER_180.PARALLAX.QWEN_GATED_FLOW.RENDER_ROOT=$GATED_RENDER_ROOT"
echo "MARKER_180.PARALLAX.QWEN_GATED_FLOW.COMPARE_SUMMARY=$GATED_COMPARE_ROOT/render_compare_qwen_multiplate_summary.json"
echo "MARKER_180.PARALLAX.QWEN_GATED_FLOW.QA_SUMMARY=$GATED_QA_ROOT/gated_batch_qa_summary.json"

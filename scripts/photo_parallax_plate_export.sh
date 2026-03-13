#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
OUT_ROOT="$LAB/output/plate_exports"

SAMPLE_ID="${1:-hover-politsia}"
APPLY_QWEN_PLAN=0
APPLY_QWEN_GATE=0
if [[ "${2:-}" == "--apply-qwen-plan" ]] || [[ "${3:-}" == "--apply-qwen-plan" ]]; then
  APPLY_QWEN_PLAN=1
fi
if [[ "${2:-}" == "--apply-qwen-gate" ]] || [[ "${3:-}" == "--apply-qwen-gate" ]]; then
  APPLY_QWEN_GATE=1
  APPLY_QWEN_PLAN=0
fi
if [[ "$APPLY_QWEN_GATE" == "1" ]]; then
  OUT_DIR="$LAB/output/plate_exports_qwen_gated/$SAMPLE_ID"
elif [[ "$APPLY_QWEN_PLAN" == "1" ]]; then
  OUT_DIR="$LAB/output/plate_exports_qwen/$SAMPLE_ID"
else
  OUT_DIR="$OUT_ROOT/$SAMPLE_ID"
fi

mkdir -p "$OUT_DIR"

cd "$LAB"

run_export() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:1434 | xargs -r kill >/dev/null 2>&1 || true
  fi

  PARALLAX_LAB_SAMPLE_ID="$SAMPLE_ID" \
  PARALLAX_LAB_PLATE_EXPORT_DIR="$OUT_DIR" \
  PARALLAX_LAB_APPLY_QWEN_PLAN="$APPLY_QWEN_PLAN" \
  PARALLAX_LAB_APPLY_QWEN_GATE="$APPLY_QWEN_GATE" \
  npx playwright test e2e/parallax_plate_export.spec.ts --reporter=line
}

attempt=1
until run_export; do
  if [[ "$attempt" -ge 3 ]]; then
    exit 1
  fi
  echo "WARN_180.PARALLAX.PLATE_EXPORT.RETRY sample=$SAMPLE_ID attempt=$attempt" >&2
  attempt=$((attempt + 1))
  sleep 2
done

echo "MARKER_180.PARALLAX.PLATE_EXPORT.SAMPLE=$SAMPLE_ID"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.MANIFEST=$OUT_DIR/plate_export_manifest.json"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.LAYOUT=$OUT_DIR/plate_layout.json"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.STACK=$OUT_DIR/plate_stack.json"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.GLOBAL_DEPTH=$OUT_DIR/global_depth_bw.png"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.COMPOSITE=$OUT_DIR/plate_export_composite.png"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.DEPTH=$OUT_DIR/plate_export_depth.png"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.QWEN_PLAN=$APPLY_QWEN_PLAN"
echo "MARKER_180.PARALLAX.PLATE_EXPORT.QWEN_GATE=$APPLY_QWEN_GATE"

if [[ "${2:-}" != "--no-open" ]] && [[ "${3:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  open "$OUT_DIR"
fi
